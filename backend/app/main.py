"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import stocks, news, sentiment, analysis, health, technical, institutional, fundamental, macro


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    if settings.is_development:
        await init_db()
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
