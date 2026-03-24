"""Multi-provider LLM service with automatic fallback.

Manages multiple LLM providers (Gemini, Groq) and automatically falls back
to the next available provider when one fails due to quota/rate-limit errors.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LLMError(Exception):
    """Base exception for LLM service errors."""
    pass


class QuotaExceededError(LLMError):
    """Raised when an LLM provider's quota or rate limit is exceeded."""

    def __init__(self, provider: str, message: str = ""):
        self.provider = provider
        super().__init__(f"Quota exceeded for {provider}: {message}")


class AllProvidersFailedError(LLMError):
    """Raised when every configured LLM provider has failed."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        summary = "; ".join(
            f"{e['provider']}: {e['error']}" for e in errors
        )
        super().__init__(f"All LLM providers failed: {summary}")


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name (e.g. 'Gemini', 'Groq')."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier used for this provider."""
        ...

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Generate a plain-text completion.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system-level instruction.
            temperature: Sampling temperature (0.0 - 1.0).
            max_tokens: Maximum tokens in the response.

        Returns:
            The generated text.

        Raises:
            QuotaExceededError: When the provider's rate/quota limit is hit.
            LLMError: On any other provider-level failure.
        """
        ...

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> dict:
        """Generate a JSON response and parse it into a Python dict.

        Args:
            prompt: The user prompt (should request JSON output).
            system_prompt: Optional system-level instruction.
            temperature: Sampling temperature (lower is more deterministic).

        Returns:
            Parsed JSON as a dict.

        Raises:
            QuotaExceededError: When the provider's rate/quota limit is hit.
            LLMError: On any other provider-level failure.
        """
        ...


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

class GeminiProvider(LLMProvider):
    """Google Gemini provider using the google-generativeai SDK."""

    _MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-initialise the Gemini client."""
        if self._client is None:
            try:
                import google.generativeai as genai
            except ImportError as exc:
                raise LLMError(
                    "google-generativeai package is not installed. "
                    "Install it with: pip install google-generativeai"
                ) from exc
            genai.configure(api_key=self._api_key)
            self._client = genai.GenerativeModel(self._MODEL)
        return self._client

    @property
    def provider_name(self) -> str:
        return "Gemini"

    @property
    def model_name(self) -> str:
        return self._MODEL

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        import asyncio

        client = self._get_client()
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        try:
            response = await asyncio.to_thread(
                client.generate_content,
                full_prompt,
                generation_config=generation_config,
            )
            if not response.text:
                raise LLMError("Gemini returned an empty response")
            return response.text

        except Exception as exc:
            self._handle_exception(exc)

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> dict:
        json_system = (system_prompt or "") + (
            "\n\nYou must respond with valid JSON only. "
            "No markdown, no explanation, just raw JSON."
        )
        raw = await self.generate_text(
            prompt=prompt,
            system_prompt=json_system.strip(),
            temperature=temperature,
        )
        return self._parse_json(raw)

    # -- helpers -------------------------------------------------------------

    def _handle_exception(self, exc: Exception) -> None:
        """Translate provider exceptions into our hierarchy."""
        exc_str = str(exc).lower()

        # google-generativeai raises google.api_core.exceptions.ResourceExhausted
        # or returns 429 status for quota issues.
        if "429" in exc_str or "resource" in exc_str and "exhausted" in exc_str:
            raise QuotaExceededError(self.provider_name, str(exc)) from exc
        if "quota" in exc_str or "rate" in exc_str:
            raise QuotaExceededError(self.provider_name, str(exc)) from exc

        raise LLMError(f"Gemini error: {exc}") from exc

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Extract and parse JSON from a possibly markdown-wrapped response."""
        text = raw.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = text.index("\n")
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Failed to parse JSON from Gemini response: {exc}") from exc


# ---------------------------------------------------------------------------
# Groq provider
# ---------------------------------------------------------------------------

class GroqProvider(LLMProvider):
    """Groq provider using the groq Python SDK (async-compatible)."""

    _MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-initialise the Groq async client."""
        if self._client is None:
            try:
                from groq import AsyncGroq
            except ImportError as exc:
                raise LLMError(
                    "groq package is not installed. "
                    "Install it with: pip install groq"
                ) from exc
            self._client = AsyncGroq(api_key=self._api_key)
        return self._client

    @property
    def provider_name(self) -> str:
        return "Groq"

    @property
    def model_name(self) -> str:
        return self._MODEL

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        client = self._get_client()

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.chat.completions.create(
                model=self._MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            if not content:
                raise LLMError("Groq returned an empty response")
            return content

        except Exception as exc:
            self._handle_exception(exc)

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> dict:
        json_system = (system_prompt or "") + (
            "\n\nYou must respond with valid JSON only. "
            "No markdown, no explanation, just raw JSON."
        )
        raw = await self.generate_text(
            prompt=prompt,
            system_prompt=json_system.strip(),
            temperature=temperature,
        )
        return self._parse_json(raw)

    # -- helpers -------------------------------------------------------------

    def _handle_exception(self, exc: Exception) -> None:
        """Translate provider exceptions into our hierarchy."""
        exc_str = str(exc).lower()

        if "rate_limit" in exc_str or "429" in exc_str or "rate limit" in exc_str:
            raise QuotaExceededError(self.provider_name, str(exc)) from exc
        if "quota" in exc_str:
            raise QuotaExceededError(self.provider_name, str(exc)) from exc

        raise LLMError(f"Groq error: {exc}") from exc

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Extract and parse JSON from a possibly markdown-wrapped response."""
        text = raw.strip()
        if text.startswith("```"):
            first_newline = text.index("\n")
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Failed to parse JSON from Groq response: {exc}") from exc


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

class LLMService:
    """Orchestrates multiple LLM providers with automatic fallback.

    Providers are tried in priority order (Gemini -> Groq). When a provider
    fails due to quota/rate-limit errors the next provider is tried
    automatically. Non-quota errors also trigger a fallback attempt so that
    transient issues on one provider do not block the entire pipeline.

    Usage::

        service = LLMService()
        result = await service.call("Summarise this article ...")
        data   = await service.call("Return JSON ...", output_format="json")
    """

    def __init__(self) -> None:
        self._providers: list[LLMProvider] = []
        self._init_providers()

    # -- initialisation ------------------------------------------------------

    def _init_providers(self) -> None:
        """Register providers whose API keys are configured."""
        if settings.GEMINI_API_KEY:
            self._providers.append(GeminiProvider(settings.GEMINI_API_KEY))
            logger.info("LLMService: Gemini provider registered (gemini-2.0-flash)")

        if settings.GROQ_API_KEY:
            self._providers.append(GroqProvider(settings.GROQ_API_KEY))
            logger.info("LLMService: Groq provider registered (llama-3.3-70b-versatile)")

        if not self._providers:
            logger.warning(
                "LLMService: No LLM providers configured. "
                "Set GEMINI_API_KEY or GROQ_API_KEY in your environment."
            )

    @property
    def available_providers(self) -> list[str]:
        """Return the names of all configured providers."""
        return [p.provider_name for p in self._providers]

    # -- public API ----------------------------------------------------------

    async def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        output_format: str = "text",
        max_tokens: int = 4096,
        purpose: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> str | dict:
        """Call an LLM provider, falling back to the next on failure.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system-level instruction.
            temperature: Sampling temperature.
            output_format: ``'text'`` or ``'json'``.
            max_tokens: Maximum response tokens (text mode only).
            purpose: Optional label for usage logging (e.g. 'sentiment').
            db: Optional database session for persisting usage logs.

        Returns:
            A string (text mode) or dict (json mode).

        Raises:
            AllProvidersFailedError: If every provider fails.
        """
        if not self._providers:
            raise AllProvidersFailedError(
                [{"provider": "none", "error": "No LLM providers configured"}]
            )

        errors: list[dict[str, str]] = []

        for provider in self._providers:
            start = time.monotonic()
            try:
                if output_format == "json":
                    result = await provider.generate_json(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                    )
                else:
                    result = await provider.generate_text(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

                elapsed_ms = int((time.monotonic() - start) * 1000)
                logger.info(
                    "LLM call succeeded: provider=%s model=%s elapsed=%dms",
                    provider.provider_name,
                    provider.model_name,
                    elapsed_ms,
                )

                # Persist usage log
                await self._log_usage(
                    db=db,
                    provider=provider.provider_name,
                    model=provider.model_name,
                    purpose=purpose,
                    success=True,
                )

                return result

            except QuotaExceededError as exc:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                logger.warning(
                    "LLM quota exceeded: provider=%s elapsed=%dms error=%s",
                    provider.provider_name,
                    elapsed_ms,
                    exc,
                )
                errors.append({
                    "provider": provider.provider_name,
                    "error": str(exc),
                    "type": "quota_exceeded",
                })
                await self._log_usage(
                    db=db,
                    provider=provider.provider_name,
                    model=provider.model_name,
                    purpose=purpose,
                    success=False,
                    error_message=str(exc),
                )

            except LLMError as exc:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                logger.error(
                    "LLM call failed: provider=%s elapsed=%dms error=%s",
                    provider.provider_name,
                    elapsed_ms,
                    exc,
                )
                errors.append({
                    "provider": provider.provider_name,
                    "error": str(exc),
                    "type": "llm_error",
                })
                await self._log_usage(
                    db=db,
                    provider=provider.provider_name,
                    model=provider.model_name,
                    purpose=purpose,
                    success=False,
                    error_message=str(exc),
                )

            except Exception as exc:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                logger.exception(
                    "Unexpected LLM error: provider=%s elapsed=%dms",
                    provider.provider_name,
                    elapsed_ms,
                )
                errors.append({
                    "provider": provider.provider_name,
                    "error": str(exc),
                    "type": "unexpected",
                })
                await self._log_usage(
                    db=db,
                    provider=provider.provider_name,
                    model=provider.model_name,
                    purpose=purpose,
                    success=False,
                    error_message=str(exc),
                )

        raise AllProvidersFailedError(errors)

    async def batch_call(
        self,
        prompts: list[str],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        output_format: str = "text",
        purpose: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> list[str | dict]:
        """Process multiple prompts sequentially with fallback support.

        Each prompt is sent through :meth:`call` independently, so a failure
        on one prompt does not prevent the rest from succeeding (each prompt
        gets its own fallback chain).

        Args:
            prompts: List of user prompts.
            system_prompt: Shared system-level instruction.
            temperature: Sampling temperature.
            output_format: ``'text'`` or ``'json'``.
            purpose: Optional label for usage logging.
            db: Optional database session for persisting usage logs.

        Returns:
            A list of results (strings or dicts) in the same order as *prompts*.
        """
        results: list[str | dict] = []
        for prompt in prompts:
            result = await self.call(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                output_format=output_format,
                purpose=purpose,
                db=db,
            )
            results.append(result)
        return results

    # -- internal helpers ----------------------------------------------------

    @staticmethod
    async def _log_usage(
        db: Optional[AsyncSession],
        provider: str,
        model: str,
        purpose: Optional[str],
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """Persist an LLM usage record if a database session is available."""
        if db is None:
            return

        try:
            from app.models.system import LLMUsageLog

            log_entry = LLMUsageLog(
                provider=provider,
                model=model,
                purpose=purpose,
                success=success,
                error_message=error_message,
            )
            db.add(log_entry)
            await db.flush()
        except Exception:
            # Logging failures must not break the main workflow.
            logger.debug("Failed to persist LLM usage log", exc_info=True)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

llm_service = LLMService()
