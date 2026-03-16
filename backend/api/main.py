"""
FINTEL — Financial Intelligence Platform
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

from api.routers import (
    companies,
    insiders,
    signals,
    metrics,
    institutional,
    composite,
    pipelines,
    dashboard,
    analyst,
)

app = FastAPI(
    title="FINTEL — Financial Intelligence Platform",
    description=(
        "Research-grade financial intelligence platform combining "
        "insider trading signals, institutional ownership, and "
        "operational business metrics for S&P 500 companies."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(companies.router, prefix="/api/companies", tags=["Companies"])
app.include_router(insiders.router, prefix="/api/insiders", tags=["Insiders"])
app.include_router(signals.router, prefix="/api/signals", tags=["Signals"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics"])
app.include_router(institutional.router, prefix="/api/institutional", tags=["Institutional"])
app.include_router(composite.router, prefix="/api/composite", tags=["Composite Scores"])
app.include_router(pipelines.router, prefix="/api/pipelines", tags=["Pipelines"])
app.include_router(analyst.router, prefix="/api/analyst", tags=["AI Analyst"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "fintel-api"}


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Resource not found"})


@app.exception_handler(500)
async def server_error_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
