"""Common schemas shared across modules."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list
