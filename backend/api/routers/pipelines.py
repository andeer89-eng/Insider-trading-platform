"""
Pipeline management endpoints — trigger and monitor ETL runs.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from models.database import get_db
from models.schemas import PipelineStatus

router = APIRouter()


@router.get("/status", response_model=List[PipelineStatus])
def get_pipeline_status(db: Session = Depends(get_db)):
    """Get the latest run status for all pipelines."""
    q = text("""
        SELECT DISTINCT ON (pipeline)
            pipeline,
            status,
            started_at AS last_run,
            records_processed,
            error_message AS error
        FROM pipeline_runs
        ORDER BY pipeline, started_at DESC
    """)
    rows = db.execute(q).mappings().all()
    return [PipelineStatus(**dict(r)) for r in rows]


@router.post("/run/sec-filings")
async def trigger_sec_pipeline(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger the SEC Form 4 ingestion pipeline."""
    from pipelines.sec_pipeline import run_sec_pipeline
    background_tasks.add_task(run_sec_pipeline)
    return {"message": "SEC filing pipeline triggered", "pipeline": "sec_filings"}


@router.post("/run/market-data")
async def trigger_market_data_pipeline(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger the market data / forward returns pipeline."""
    from pipelines.market_data_pipeline import run_market_data_pipeline
    background_tasks.add_task(run_market_data_pipeline)
    return {"message": "Market data pipeline triggered", "pipeline": "market_data"}


@router.post("/run/institutional")
async def trigger_institutional_pipeline(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger the 13F institutional holdings pipeline."""
    from pipelines.institutional_pipeline import run_institutional_pipeline
    background_tasks.add_task(run_institutional_pipeline)
    return {"message": "Institutional holdings pipeline triggered", "pipeline": "institutional_13f"}


@router.post("/run/signal-scoring")
async def trigger_signal_scoring(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger the signal scoring engine over recent transactions."""
    from signals.scorer import run_signal_scoring
    background_tasks.add_task(run_signal_scoring)
    return {"message": "Signal scoring pipeline triggered", "pipeline": "signal_scoring"}


@router.get("/runs/history")
def get_pipeline_history(
    pipeline: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get pipeline run history."""
    conditions = ["1=1"]
    params: dict = {"limit": limit}

    if pipeline:
        conditions.append("pipeline = :pipeline")
        params["pipeline"] = pipeline

    where = " AND ".join(conditions)
    q = text(f"""
        SELECT pipeline, status, started_at, ended_at, records_processed, error_message
        FROM pipeline_runs
        WHERE {where}
        ORDER BY started_at DESC
        LIMIT :limit
    """)
    rows = db.execute(q, params).mappings().all()
    return [dict(r) for r in rows]
