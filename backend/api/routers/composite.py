"""
Composite opportunity score endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional

from models.database import get_db
from models.schemas import CompositeScore
from lib.cache import get_cache, set_cache

router = APIRouter()


@router.get("/scores", response_model=List[CompositeScore])
def get_composite_scores(
    sector: Optional[str] = None,
    min_score: float = Query(0.0, ge=0, le=10),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Latest composite opportunity scores, ranked."""
    cache_key = f"composite_scores:{sector or 'all'}:{min_score}:{limit}"
    cached = get_cache(cache_key)
    if cached is not None:
        return [CompositeScore(**r) for r in cached]

    sector_filter = "AND c.sector = :sector" if sector else ""
    params: dict = {"min_score": min_score, "limit": limit}
    if sector:
        params["sector"] = sector

    # Inner query picks the most recent score per company (DISTINCT ON + date DESC).
    # Outer query filters by min_score and sorts by composite_score, with DB-level LIMIT.
    q = text(f"""
        SELECT * FROM (
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
            WHERE 1=1 {sector_filter}
            ORDER BY ccs.company_id, ccs.date DESC
        ) latest
        WHERE composite_score >= :min_score
        ORDER BY composite_score DESC NULLS LAST
        LIMIT :limit
    """)
    rows = db.execute(q, params).mappings().all()
    result = [dict(r) for r in rows]
    set_cache(cache_key, result, ttl=300)
    return [CompositeScore(**r) for r in result]


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
    cache_key = f"leaderboard:{sector or 'all'}:{sort_by}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    sector_filter = "AND c.sector = :sector" if sector else ""
    params: dict = {"sector": sector} if sector else {}

    # CTE pre-aggregates buys_30d in one pass (eliminates correlated subquery × N rows).
    # DISTINCT ON + ORDER BY company_id, date DESC picks the most recent score per company.
    # Final ORDER BY + LIMIT 50 is done in the database, not Python.
    q = text(f"""
        WITH recent_buys AS (
            SELECT company_id, COUNT(*) AS buys_30d
            FROM insider_transactions
            WHERE transaction_type IN ('Buy', 'Purchase')
              AND transaction_date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY company_id
        ),
        latest_scores AS (
            SELECT DISTINCT ON (ccs.company_id)
                ccs.company_id,
                ccs.date AS score_date,
                ccs.insider_score,
                ccs.institutional_score,
                ccs.business_momentum_score,
                ccs.industry_score,
                ccs.composite_score,
                ccs.insider_alignment
            FROM company_composite_scores ccs
            ORDER BY ccs.company_id, ccs.date DESC
        )
        SELECT
            ls.company_id,
            c.ticker,
            c.name AS company_name,
            c.sector,
            c.market_cap,
            ls.score_date,
            ls.insider_score,
            ls.institutional_score,
            ls.business_momentum_score,
            ls.industry_score,
            ls.composite_score,
            ls.insider_alignment,
            COALESCE(rb.buys_30d, 0) AS buys_30d
        FROM latest_scores ls
        JOIN companies c ON c.id = ls.company_id
        LEFT JOIN recent_buys rb ON rb.company_id = ls.company_id
        WHERE 1=1 {sector_filter}
        ORDER BY ls.{sort_by} DESC NULLS LAST
        LIMIT 50
    """)
    rows = db.execute(q, params).mappings().all()
    result = [dict(r) for r in rows]
    set_cache(cache_key, result, ttl=300)
    return result
