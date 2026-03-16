"""
Dashboard endpoints — homepage aggregations and summary views.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, timedelta
from typing import List, Optional

from models.database import get_db
from models.schemas import HomepageData, TopInsiderSignal, CompositeScore, ClusterEvent
from lib.cache import get_cache, set_cache

router = APIRouter()


@router.get("/dashboard", response_model=HomepageData)
def get_dashboard(db: Session = Depends(get_db)):
    """Homepage dashboard with top signals, scores, and cluster events."""
    cache_key = "dashboard"
    cached = get_cache(cache_key)
    if cached is not None:
        return HomepageData(**cached)

    today = date.today()
    lookback = today - timedelta(days=30)

    # Top insider signals (last 30 days, buys only, score >= 5)
    signals_q = text("""
        SELECT
            it.id AS transaction_id,
            c.ticker,
            c.name AS company_name,
            c.sector,
            i.name AS insider_name,
            i.role AS insider_role,
            it.transaction_date,
            it.transaction_type,
            it.shares,
            it.price,
            it.transaction_value,
            it.ownership_change_pct,
            iss.score AS signal_score,
            iss.cluster_flag,
            iss.insider_skill_score,
            iss.signal_reason
        FROM insider_transactions it
        JOIN companies c ON c.id = it.company_id
        LEFT JOIN insiders i ON i.id = it.insider_id
        LEFT JOIN insider_signal_scores iss ON iss.transaction_id = it.id
        WHERE it.transaction_type IN ('Buy', 'Purchase')
          AND it.transaction_date >= :lookback
        ORDER BY iss.score DESC NULLS LAST, it.transaction_value DESC NULLS LAST
        LIMIT 20
    """)
    signals_rows = db.execute(signals_q, {"lookback": lookback}).mappings().all()

    # Top composite scores — dedup in subquery, sort + limit in DB
    composite_q = text("""
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
            ORDER BY ccs.company_id, ccs.date DESC
        ) latest
        ORDER BY composite_score DESC NULLS LAST
        LIMIT 10
    """)
    composite_sorted = db.execute(composite_q).mappings().all()

    # Recent cluster events
    cluster_q = text("""
        SELECT
            ice.id,
            ice.company_id,
            c.ticker,
            c.name AS company_name,
            ice.start_date,
            ice.end_date,
            ice.insider_count,
            ice.total_value,
            ice.unique_roles,
            ice.cluster_score
        FROM insider_cluster_events ice
        JOIN companies c ON c.id = ice.company_id
        WHERE ice.end_date >= :lookback
        ORDER BY ice.cluster_score DESC NULLS LAST, ice.end_date DESC
        LIMIT 10
    """)
    cluster_rows = db.execute(cluster_q, {"lookback": lookback}).mappings().all()

    # Today's summary stats
    stats_q = text("""
        SELECT
            COUNT(*) AS total_transactions,
            COALESCE(SUM(CASE WHEN transaction_type IN ('Buy', 'Purchase')
                             THEN transaction_value ELSE 0 END), 0) AS buy_value
        FROM insider_transactions
        WHERE transaction_date = :today
    """)
    stats = db.execute(stats_q, {"today": today}).mappings().first()

    payload = HomepageData(
        top_signals=[TopInsiderSignal(**dict(r)) for r in signals_rows],
        top_composite_scores=[CompositeScore(**dict(r)) for r in composite_sorted],
        recent_cluster_events=[ClusterEvent(**dict(r)) for r in cluster_rows],
        total_transactions_today=stats["total_transactions"] if stats else 0,
        total_buy_value_today=float(stats["buy_value"] or 0) if stats else 0.0,
        market_date=today,
    )
    set_cache(cache_key, payload.model_dump(), ttl=60)
    return payload


@router.get("/dashboard/signals/top", response_model=List[TopInsiderSignal])
def get_top_signals(
    days: int = Query(30, ge=1, le=365),
    min_score: float = Query(5.0, ge=0, le=10),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Top insider signals within a lookback window."""
    lookback = date.today() - timedelta(days=days)
    q = text("""
        SELECT
            it.id AS transaction_id,
            c.ticker, c.name AS company_name, c.sector,
            i.name AS insider_name, i.role AS insider_role,
            it.transaction_date, it.transaction_type,
            it.shares, it.price, it.transaction_value,
            it.ownership_change_pct,
            iss.score AS signal_score,
            iss.cluster_flag, iss.insider_skill_score, iss.signal_reason
        FROM insider_transactions it
        JOIN companies c ON c.id = it.company_id
        LEFT JOIN insiders i ON i.id = it.insider_id
        LEFT JOIN insider_signal_scores iss ON iss.transaction_id = it.id
        WHERE it.transaction_type IN ('Buy', 'Purchase')
          AND it.transaction_date >= :lookback
          AND (iss.score >= :min_score OR iss.score IS NULL)
        ORDER BY iss.score DESC NULLS LAST
        LIMIT :limit
    """)
    rows = db.execute(q, {"lookback": lookback, "min_score": min_score, "limit": limit}).mappings().all()
    return [TopInsiderSignal(**dict(r)) for r in rows]
