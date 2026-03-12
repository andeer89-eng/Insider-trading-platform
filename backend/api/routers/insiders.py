"""
Insider trading endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, timedelta
from typing import List, Optional

from models.database import get_db
from models.schemas import InsiderTransactionSummary, InsiderTransactionDetail

router = APIRouter()


@router.get("/transactions", response_model=List[InsiderTransactionSummary])
def list_transactions(
    ticker: Optional[str] = None,
    transaction_type: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    min_value: Optional[float] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List insider transactions with filters."""
    lookback = date.today() - timedelta(days=days)
    conditions = ["it.transaction_date >= :lookback"]
    params: dict = {"lookback": lookback, "limit": limit, "offset": offset}

    if ticker:
        conditions.append("c.ticker = :ticker")
        params["ticker"] = ticker.upper()
    if transaction_type:
        conditions.append("it.transaction_type = :tx_type")
        params["tx_type"] = transaction_type
    if min_value:
        conditions.append("it.transaction_value >= :min_value")
        params["min_value"] = min_value

    where = " AND ".join(conditions)
    q = text(f"""
        SELECT
            it.id, it.company_id, it.insider_id,
            it.transaction_date, it.transaction_type,
            it.shares, it.price, it.transaction_value,
            it.ownership_before, it.ownership_after, it.ownership_change_pct,
            it.filing_type, it.filing_url,
            i.name AS insider_name, i.role AS insider_role,
            c.ticker, c.name AS company_name,
            iss.score AS signal_score, iss.cluster_flag
        FROM insider_transactions it
        JOIN companies c ON c.id = it.company_id
        LEFT JOIN insiders i ON i.id = it.insider_id
        LEFT JOIN insider_signal_scores iss ON iss.transaction_id = it.id
        WHERE {where}
        ORDER BY it.transaction_date DESC, iss.score DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(q, params).mappings().all()
    return [InsiderTransactionSummary(**dict(r)) for r in rows]


@router.get("/transactions/{transaction_id}", response_model=InsiderTransactionDetail)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific transaction."""
    q = text("""
        SELECT
            it.*, i.name AS insider_name, i.role AS insider_role,
            c.ticker, c.name AS company_name,
            iss.score AS signal_score, iss.cluster_flag,
            ito.return_7d, ito.return_30d, ito.return_90d, ito.return_1y
        FROM insider_transactions it
        JOIN companies c ON c.id = it.company_id
        LEFT JOIN insiders i ON i.id = it.insider_id
        LEFT JOIN insider_signal_scores iss ON iss.transaction_id = it.id
        LEFT JOIN insider_trade_outcomes ito ON ito.transaction_id = it.id
        WHERE it.id = :id
    """)
    row = db.execute(q, {"id": transaction_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return InsiderTransactionDetail(**dict(row))


@router.get("/company/{ticker}", response_model=List[InsiderTransactionSummary])
def get_company_insiders(
    ticker: str,
    days: int = Query(365, ge=1, le=3650),
    transaction_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """All insider transactions for a specific company."""
    lookback = date.today() - timedelta(days=days)
    conditions = ["c.ticker = :ticker", "it.transaction_date >= :lookback"]
    params: dict = {"ticker": ticker.upper(), "lookback": lookback, "limit": limit}

    if transaction_type:
        conditions.append("it.transaction_type = :tx_type")
        params["tx_type"] = transaction_type

    where = " AND ".join(conditions)
    q = text(f"""
        SELECT
            it.id, it.company_id, it.insider_id,
            it.transaction_date, it.transaction_type,
            it.shares, it.price, it.transaction_value,
            it.ownership_before, it.ownership_after, it.ownership_change_pct,
            it.filing_type, it.filing_url,
            i.name AS insider_name, i.role AS insider_role,
            c.ticker, c.name AS company_name,
            iss.score AS signal_score, iss.cluster_flag
        FROM insider_transactions it
        JOIN companies c ON c.id = it.company_id
        LEFT JOIN insiders i ON i.id = it.insider_id
        LEFT JOIN insider_signal_scores iss ON iss.transaction_id = it.id
        WHERE {where}
        ORDER BY it.transaction_date DESC
        LIMIT :limit
    """)
    rows = db.execute(q, params).mappings().all()
    return [InsiderTransactionSummary(**dict(r)) for r in rows]


@router.get("/clusters/recent")
def get_recent_clusters(
    days: int = Query(90, ge=1, le=365),
    min_insiders: int = Query(2, ge=2, le=20),
    db: Session = Depends(get_db),
):
    """Recent insider cluster buying events."""
    lookback = date.today() - timedelta(days=days)
    q = text("""
        SELECT
            ice.id, ice.company_id, c.ticker, c.name AS company_name,
            c.sector, ice.start_date, ice.end_date,
            ice.insider_count, ice.total_value,
            ice.unique_roles, ice.cluster_score
        FROM insider_cluster_events ice
        JOIN companies c ON c.id = ice.company_id
        WHERE ice.end_date >= :lookback
          AND ice.insider_count >= :min_insiders
        ORDER BY ice.cluster_score DESC NULLS LAST, ice.end_date DESC
        LIMIT 50
    """)
    rows = db.execute(q, {"lookback": lookback, "min_insiders": min_insiders}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/insider/{insider_id}/history")
def get_insider_history(insider_id: int, db: Session = Depends(get_db)):
    """Historical performance of a specific insider."""
    q = text("""
        SELECT
            it.transaction_date, it.transaction_type,
            it.shares, it.price, it.transaction_value,
            it.ownership_change_pct,
            iss.score AS signal_score,
            ito.return_7d, ito.return_30d, ito.return_90d, ito.return_1y,
            ito.alpha_30d, ito.alpha_90d
        FROM insider_transactions it
        LEFT JOIN insider_signal_scores iss ON iss.transaction_id = it.id
        LEFT JOIN insider_trade_outcomes ito ON ito.transaction_id = it.id
        WHERE it.insider_id = :insider_id
        ORDER BY it.transaction_date DESC
    """)
    trades = db.execute(q, {"insider_id": insider_id}).mappings().all()
    if not trades:
        raise HTTPException(status_code=404, detail="Insider not found")

    # Compute skill stats
    buys = [t for t in trades if t["transaction_type"] in ("Buy", "Purchase")]
    positive_30d = [t for t in buys if t["return_30d"] and t["return_30d"] > 0]
    win_rate = len(positive_30d) / len(buys) if buys else 0
    avg_alpha = sum(t["alpha_30d"] for t in buys if t["alpha_30d"]) / max(len(buys), 1)

    return {
        "insider_id": insider_id,
        "total_trades": len(trades),
        "total_buys": len(buys),
        "win_rate_30d": round(win_rate, 4),
        "avg_alpha_30d": round(avg_alpha, 4),
        "trades": [dict(t) for t in trades],
    }
