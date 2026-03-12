"""
Company endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional

from models.database import get_db
from models.schemas import CompanySummary, CompanyDetail

router = APIRouter()


@router.get("", response_model=List[CompanySummary])
def list_companies(
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List all S&P 500 companies with optional filters."""
    conditions = ["1=1"]
    params = {"limit": limit, "offset": offset}

    if sector:
        conditions.append("sector = :sector")
        params["sector"] = sector
    if industry:
        conditions.append("industry = :industry")
        params["industry"] = industry
    if search:
        conditions.append("(name ILIKE :search OR ticker ILIKE :search)")
        params["search"] = f"%{search}%"

    where = " AND ".join(conditions)
    q = text(f"""
        SELECT id, ticker, name, sector, industry, market_cap, exchange, logo_url
        FROM companies
        WHERE {where}
        ORDER BY market_cap DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(q, params).mappings().all()
    return [CompanySummary(**dict(r)) for r in rows]


@router.get("/sectors")
def list_sectors(db: Session = Depends(get_db)):
    """List all available sectors."""
    q = text("SELECT DISTINCT sector FROM companies WHERE sector IS NOT NULL ORDER BY sector")
    rows = db.execute(q).fetchall()
    return [r[0] for r in rows]


@router.get("/{ticker}", response_model=CompanyDetail)
def get_company(ticker: str, db: Session = Depends(get_db)):
    """Get detailed company profile with latest composite score."""
    q = text("""
        SELECT
            c.*,
            ccs.composite_score,
            ccs.insider_score,
            ccs.institutional_score,
            ccs.business_momentum_score
        FROM companies c
        LEFT JOIN LATERAL (
            SELECT composite_score, insider_score, institutional_score, business_momentum_score
            FROM company_composite_scores
            WHERE company_id = c.id
            ORDER BY date DESC
            LIMIT 1
        ) ccs ON TRUE
        WHERE c.ticker = :ticker
    """)
    row = db.execute(q, {"ticker": ticker.upper()}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")
    return CompanyDetail(**dict(row))


@router.get("/{ticker}/summary")
def get_company_summary(ticker: str, db: Session = Depends(get_db)):
    """Full company summary: recent trades, latest metrics, scores."""
    company_q = text("SELECT id, ticker, name, sector, industry FROM companies WHERE ticker = :ticker")
    company = db.execute(company_q, {"ticker": ticker.upper()}).mappings().first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    company_id = company["id"]

    # Recent transactions
    trades_q = text("""
        SELECT it.transaction_date, it.transaction_type, it.shares, it.price,
               it.transaction_value, it.ownership_change_pct,
               i.name AS insider_name, i.role AS insider_role,
               iss.score AS signal_score
        FROM insider_transactions it
        LEFT JOIN insiders i ON i.id = it.insider_id
        LEFT JOIN insider_signal_scores iss ON iss.transaction_id = it.id
        WHERE it.company_id = :company_id
        ORDER BY it.transaction_date DESC
        LIMIT 10
    """)
    trades = db.execute(trades_q, {"company_id": company_id}).mappings().all()

    # Latest composite score
    score_q = text("""
        SELECT * FROM company_composite_scores
        WHERE company_id = :company_id
        ORDER BY date DESC LIMIT 1
    """)
    score = db.execute(score_q, {"company_id": company_id}).mappings().first()

    # Latest metric values (most recent per metric)
    metrics_q = text("""
        SELECT DISTINCT ON (cmv.metric_id)
            m.name, m.display_name, m.category, m.unit,
            cmv.date, cmv.value, cmv.yoy_growth
        FROM company_metric_values cmv
        JOIN metrics m ON m.id = cmv.metric_id
        WHERE cmv.company_id = :company_id
        ORDER BY cmv.metric_id, cmv.date DESC
        LIMIT 30
    """)
    metrics_rows = db.execute(metrics_q, {"company_id": company_id}).mappings().all()

    return {
        "company": dict(company),
        "composite_score": dict(score) if score else None,
        "recent_trades": [dict(r) for r in trades],
        "key_metrics": [dict(r) for r in metrics_rows],
    }
