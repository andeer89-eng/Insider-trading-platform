"""
Signal engine endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, timedelta
from typing import List, Optional

from models.database import get_db
from models.schemas import InsiderSignalScore, TopInsiderSignal

router = APIRouter()


@router.get("/scores", response_model=List[InsiderSignalScore])
def list_signal_scores(
    min_score: float = Query(5.0, ge=0, le=10),
    days: int = Query(30, ge=1, le=365),
    cluster_only: bool = False,
    db: Session = Depends(get_db),
):
    """List high-conviction insider signal scores."""
    lookback = date.today() - timedelta(days=days)
    conditions = ["it.transaction_date >= :lookback", "iss.score >= :min_score"]
    params: dict = {"lookback": lookback, "min_score": min_score}

    if cluster_only:
        conditions.append("iss.cluster_flag = TRUE")

    where = " AND ".join(conditions)
    q = text(f"""
        SELECT iss.*
        FROM insider_signal_scores iss
        JOIN insider_transactions it ON it.id = iss.transaction_id
        WHERE {where}
        ORDER BY iss.score DESC
        LIMIT 200
    """)
    rows = db.execute(q, params).mappings().all()
    return [InsiderSignalScore(**dict(r)) for r in rows]


@router.get("/scores/{transaction_id}", response_model=InsiderSignalScore)
def get_signal_score(transaction_id: int, db: Session = Depends(get_db)):
    """Get signal score breakdown for a specific transaction."""
    q = text("SELECT * FROM insider_signal_scores WHERE transaction_id = :id")
    row = db.execute(q, {"id": transaction_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Signal score not found for this transaction")
    return InsiderSignalScore(**dict(row))


@router.get("/sector-heatmap")
def get_sector_heatmap(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
):
    """Aggregate insider buying sentiment by sector."""
    lookback = date.today() - timedelta(days=days)
    q = text("""
        SELECT
            c.sector,
            COUNT(*) AS total_trades,
            COUNT(CASE WHEN it.transaction_type IN ('Buy', 'Purchase') THEN 1 END) AS buys,
            COUNT(CASE WHEN it.transaction_type IN ('Sell', 'Sale') THEN 1 END) AS sells,
            COALESCE(SUM(CASE WHEN it.transaction_type IN ('Buy', 'Purchase')
                         THEN it.transaction_value ELSE 0 END), 0) AS total_buy_value,
            COALESCE(SUM(CASE WHEN it.transaction_type IN ('Sell', 'Sale')
                         THEN it.transaction_value ELSE 0 END), 0) AS total_sell_value,
            COALESCE(AVG(iss.score), 0) AS avg_signal_score
        FROM insider_transactions it
        JOIN companies c ON c.id = it.company_id
        LEFT JOIN insider_signal_scores iss ON iss.transaction_id = it.id
        WHERE it.transaction_date >= :lookback
          AND c.sector IS NOT NULL
        GROUP BY c.sector
        ORDER BY total_buy_value DESC
    """)
    rows = db.execute(q, {"lookback": lookback}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/conviction-timeline")
def get_conviction_timeline(
    ticker: Optional[str] = None,
    days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
):
    """Time-series of insider buying conviction (score) for charting."""
    lookback = date.today() - timedelta(days=days)
    conditions = ["it.transaction_date >= :lookback",
                  "it.transaction_type IN ('Buy', 'Purchase')"]
    params: dict = {"lookback": lookback}

    if ticker:
        conditions.append("c.ticker = :ticker")
        params["ticker"] = ticker.upper()

    where = " AND ".join(conditions)
    q = text(f"""
        SELECT
            it.transaction_date AS date,
            c.ticker,
            c.name AS company_name,
            COALESCE(iss.score, 5) AS signal_score,
            it.transaction_value,
            iss.cluster_flag
        FROM insider_transactions it
        JOIN companies c ON c.id = it.company_id
        LEFT JOIN insider_signal_scores iss ON iss.transaction_id = it.id
        WHERE {where}
        ORDER BY it.transaction_date
    """)
    rows = db.execute(q, params).mappings().all()
    return [dict(r) for r in rows]


@router.get("/performance/outcomes")
def get_trade_outcomes(
    min_score: float = Query(6.0, ge=0, le=10),
    db: Session = Depends(get_db),
):
    """Aggregate forward return outcomes by signal score bucket."""
    q = text("""
        SELECT
            FLOOR(iss.score)::INT AS score_bucket,
            COUNT(*) AS n_trades,
            ROUND(AVG(ito.return_30d) * 100, 2) AS avg_return_30d,
            ROUND(AVG(ito.return_90d) * 100, 2) AS avg_return_90d,
            ROUND(AVG(ito.return_1y) * 100, 2) AS avg_return_1y,
            ROUND(AVG(ito.alpha_30d) * 100, 2) AS avg_alpha_30d,
            ROUND(AVG(ito.alpha_90d) * 100, 2) AS avg_alpha_90d,
            ROUND(COUNT(CASE WHEN ito.return_30d > 0 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS win_rate_30d
        FROM insider_signal_scores iss
        JOIN insider_trade_outcomes ito ON ito.transaction_id = iss.transaction_id
        JOIN insider_transactions it ON it.id = iss.transaction_id
        WHERE it.transaction_type IN ('Buy', 'Purchase')
          AND iss.score IS NOT NULL
        GROUP BY score_bucket
        ORDER BY score_bucket
    """)
    rows = db.execute(q).mappings().all()
    return [dict(r) for r in rows]
