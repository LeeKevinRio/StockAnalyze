"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import stocks, news, sentiment, analysis, health, technical, institutional, fundamental, macro, auth, watchlist

# Make app.* INFO logs visible in production (uvicorn only configures its own
# loggers; without this the root logger stays at WARNING and swallows them).
logging.basicConfig(
    level=logging.DEBUG if settings.APP_DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

# Refuse to serve auth with the known default secret outside development —
# anyone reading the repo could forge login tokens.
if settings.JWT_SECRET == "dev-insecure-change-me" and not settings.is_development:
    raise RuntimeError(
        "JWT_SECRET is still the insecure default. Set the JWT_SECRET "
        "environment variable (Render: generateValue in render.yaml)."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup — create tables if missing (idempotent; safe in prod & dev).
    try:
        await init_db()
    except Exception:
        # Don't crash the app if the DB is briefly unavailable at boot.
        logger.exception("init_db failed at startup")
    yield
    # Shutdown


app = FastAPI(
    title="台股分析平台 API",
    description="Taiwan Stock Analysis Platform - 五維度深度分析",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["Health"])
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["Stocks"])
app.include_router(news.router, prefix="/api/v1/news", tags=["News"])
app.include_router(sentiment.router, prefix="/api/v1/sentiment", tags=["Sentiment"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(technical.router, prefix="/api/v1/technical", tags=["Technical"])
app.include_router(institutional.router, prefix="/api/v1/institutional", tags=["Institutional"])
app.include_router(fundamental.router, prefix="/api/v1/fundamental", tags=["Fundamental"])
app.include_router(macro.router, prefix="/api/v1/macro", tags=["Macro"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(watchlist.router, prefix="/api/v1/watchlist", tags=["Watchlist"])
