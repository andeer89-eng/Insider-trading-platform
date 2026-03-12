"""
Composite opportunity score endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional

from models.database import get_db
from models.schemas import CompositeScore

router = APIRouter()


@router.get("/scores", response_model=List[CompositeScore])
def get_composite_scores(
    sector: Optional[str] = None,
    min_score: float = Query(0.0, ge=0, le=10),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Latest composite opportunity scores, ranked."""
    conditions = ["1=1"]
    params: dict = {"min_score": min_score, "limit": limit}

    if sector:
        conditions.append("c.sector = :sector")
        params["sector"] = sector

    where = " AND ".join(conditions)
    q = text(f"""
        SELECT DISTINCT ON (ccs.company_id)
            ccs.company_id,
            c.ticker,
            c.name AS company_name,
            c.sector,
            ccs.date,
            ccs.insider_score,
            ccs.institutional_score,
            ccs.business_momentum_score,
            ccs.industry_score,
            ccs.composite_score,
            ccs.insider_alignment
        FROM company_composite_scores ccs
        JOIN companies c ON c.id = ccs.company_id
        WHERE {where}
          AND ccs.composite_score >= :min_score
        ORDER BY ccs.company_id, ccs.date DESC
    """)
    rows = db.execute(q, params).mappings().all()
    sorted_rows = sorted(rows, key=lambda x: x["composite_score"] or 0, reverse=True)[:limit]
    return [CompositeScore(**dict(r)) for r in sorted_rows]


@router.get("/score/{ticker}")
def get_company_composite(ticker: str, db: Session = Depends(get_db)):
    """Composite score history for a company."""
    q = text("""
        SELECT
            ccs.date, ccs.insider_score, ccs.institutional_score,
            ccs.business_momentum_score, ccs.industry_score,
            ccs.composite_score, ccs.insider_alignment
        FROM company_composite_scores ccs
        JOIN companies c ON c.id = ccs.company_id
        WHERE c.ticker = :ticker
        ORDER BY ccs.date DESC
        LIMIT 60
    """)
    rows = db.execute(q, {"ticker": ticker.upper()}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/leaderboard")
def get_leaderboard(
    sector: Optional[str] = None,
    sort_by: str = Query("composite_score", regex="^(composite_score|insider_score|institutional_score|business_momentum_score)$"),
    db: Session = Depends(get_db),
):
    """
    Leaderboard of top companies by composite opportunity score.
    Powers the main discovery table.
    """
    conditions = ["1=1"]
    params: dict = {}

    if sector:
        conditions.append("c.sector = :sector")
        params["sector"] = sector

    where = " AND ".join(conditions)
    q = text(f"""
        SELECT DISTINCT ON (ccs.company_id)
            ccs.company_id,
            c.ticker,
            c.name AS company_name,
            c.sector,
            c.market_cap,
            ccs.date AS score_date,
            ccs.insider_score,
            ccs.institutional_score,
            ccs.business_momentum_score,
            ccs.industry_score,
            ccs.composite_score,
            ccs.insider_alignment,
            -- Recent buy count
            (SELECT COUNT(*) FROM insider_transactions it
             WHERE it.company_id = ccs.company_id
               AND it.transaction_type IN ('Buy','Purchase')
               AND it.transaction_date >= CURRENT_DATE - INTERVAL '30 days') AS buys_30d
        FROM company_composite_scores ccs
        JOIN companies c ON c.id = ccs.company_id
        WHERE {where}
        ORDER BY ccs.company_id, ccs.date DESC
    """)
    rows = db.execute(q, params).mappings().all()
    sorted_rows = sorted(rows, key=lambda x: x[sort_by] or 0, reverse=True)[:50]
    return [dict(r) for r in sorted_rows]
