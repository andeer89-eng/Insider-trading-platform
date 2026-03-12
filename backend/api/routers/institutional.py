"""
Institutional ownership endpoints (13F data).
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional

from models.database import get_db
from models.schemas import CompanyOwnership

router = APIRouter()


@router.get("/company/{ticker}", response_model=CompanyOwnership)
def get_company_ownership(ticker: str, db: Session = Depends(get_db)):
    """Institutional ownership breakdown for a company."""
    company_q = text("SELECT id, ticker FROM companies WHERE ticker = :ticker")
    company = db.execute(company_q, {"ticker": ticker.upper()}).mappings().first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    company_id = company["id"]

    # Latest quarter summary
    summary_q = text("""
        SELECT
            SUM(ih.shares) AS total_institutional_shares,
            COUNT(DISTINCT ih.firm_id) AS num_holders,
            SUM(ih.change_shares) AS net_change_last_quarter
        FROM institutional_holdings ih
        WHERE ih.company_id = :company_id
          AND ih.quarter = (
              SELECT MAX(quarter) FROM institutional_holdings WHERE company_id = :company_id
          )
    """)
    summary = db.execute(summary_q, {"company_id": company_id}).mappings().first()

    # Top holders
    holders_q = text("""
        SELECT
            f.name AS firm_name, f.type AS firm_type,
            ih.quarter, ih.shares, ih.value, ih.change_shares, ih.change_pct
        FROM institutional_holdings ih
        JOIN institutional_firms f ON f.id = ih.firm_id
        WHERE ih.company_id = :company_id
          AND ih.quarter = (
              SELECT MAX(quarter) FROM institutional_holdings WHERE company_id = :company_id
          )
        ORDER BY ih.shares DESC NULLS LAST
        LIMIT 20
    """)
    holders = db.execute(holders_q, {"company_id": company_id}).mappings().all()

    # Compute shares outstanding for ownership %
    shares_q = text("""
        SELECT value AS shares_outstanding
        FROM company_metric_values cmv
        JOIN metrics m ON m.id = cmv.metric_id
        WHERE cmv.company_id = :company_id
          AND m.name = 'shares_outstanding'
        ORDER BY cmv.date DESC LIMIT 1
    """)
    shares_row = db.execute(shares_q, {"company_id": company_id}).mappings().first()
    shares_outstanding = float(shares_row["shares_outstanding"]) * 1_000_000 if shares_row else None

    total_inst = float(summary["total_institutional_shares"] or 0)
    ownership_pct = (total_inst / shares_outstanding * 100) if shares_outstanding and shares_outstanding > 0 else None

    # Accumulation score: net buyers vs sellers ratio
    accum_q = text("""
        SELECT
            COUNT(CASE WHEN change_shares > 0 THEN 1 END) AS n_buyers,
            COUNT(CASE WHEN change_shares < 0 THEN 1 END) AS n_sellers,
            COUNT(*) AS total
        FROM institutional_holdings
        WHERE company_id = :company_id
          AND quarter = (SELECT MAX(quarter) FROM institutional_holdings WHERE company_id = :company_id)
    """)
    accum = db.execute(accum_q, {"company_id": company_id}).mappings().first()
    n_buyers = accum["n_buyers"] or 0
    total_h = accum["total"] or 1
    accum_score = round((n_buyers / total_h) * 10, 2) if total_h > 0 else None

    return CompanyOwnership(
        company_id=company_id,
        ticker=company["ticker"],
        total_institutional_shares=int(total_inst) if total_inst else None,
        institutional_ownership_pct=round(ownership_pct, 2) if ownership_pct else None,
        num_holders=summary["num_holders"],
        top_holders=[dict(h) for h in holders],
        net_change_last_quarter=summary["net_change_last_quarter"],
        accumulation_score=accum_score,
    )


@router.get("/firm/{firm_name}/holdings")
def get_firm_holdings(
    firm_name: str,
    db: Session = Depends(get_db),
):
    """Holdings of a specific institutional firm."""
    q = text("""
        SELECT
            c.ticker, c.name AS company_name, c.sector,
            ih.quarter, ih.shares, ih.value,
            ih.change_shares, ih.change_pct
        FROM institutional_holdings ih
        JOIN institutional_firms f ON f.id = ih.firm_id
        JOIN companies c ON c.id = ih.company_id
        WHERE f.name ILIKE :name
          AND ih.quarter = (
              SELECT MAX(quarter) FROM institutional_holdings WHERE firm_id = f.id
          )
        ORDER BY ih.value DESC NULLS LAST
        LIMIT 100
    """)
    rows = db.execute(q, {"name": f"%{firm_name}%"}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/net-accumulation")
def get_net_accumulation(
    sector: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Companies with strongest net institutional accumulation last quarter."""
    conditions = ["1=1"]
    params: dict = {}

    if sector:
        conditions.append("c.sector = :sector")
        params["sector"] = sector

    where = " AND ".join(conditions)
    q = text(f"""
        SELECT
            c.ticker, c.name AS company_name, c.sector,
            ina.quarter, ina.net_change,
            ina.num_buyers, ina.num_sellers,
            ina.shares_bought, ina.shares_sold,
            ROUND(ina.num_buyers * 10.0 / NULLIF(ina.num_buyers + ina.num_sellers, 0), 2) AS accum_score
        FROM institutional_net_accumulation ina
        JOIN companies c ON c.id = ina.company_id
        WHERE {where}
          AND ina.quarter = (SELECT MAX(quarter) FROM institutional_holdings)
        ORDER BY ina.net_change DESC NULLS LAST
        LIMIT 50
    """)
    rows = db.execute(q, params).mappings().all()
    return [dict(r) for r in rows]


@router.get("/alignment/{ticker}")
def get_insider_institutional_alignment(ticker: str, db: Session = Depends(get_db)):
    """
    Alignment score: are insiders and institutions both buying?
    High alignment = strong composite signal.
    """
    company_q = text("SELECT id FROM companies WHERE ticker = :ticker")
    company = db.execute(company_q, {"ticker": ticker.upper()}).fetchone()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company_id = company[0]

    # Insider buying last 90 days
    insider_q = text("""
        SELECT
            COUNT(*) AS buy_count,
            COALESCE(SUM(transaction_value), 0) AS buy_value
        FROM insider_transactions
        WHERE company_id = :company_id
          AND transaction_type IN ('Buy', 'Purchase')
          AND transaction_date >= CURRENT_DATE - INTERVAL '90 days'
    """)
    insider_data = db.execute(insider_q, {"company_id": company_id}).mappings().first()

    # Institutional net change last quarter
    inst_q = text("""
        SELECT
            SUM(change_shares) AS net_inst_change,
            COUNT(CASE WHEN change_shares > 0 THEN 1 END) AS inst_buyers
        FROM institutional_holdings
        WHERE company_id = :company_id
          AND quarter = (SELECT MAX(quarter) FROM institutional_holdings WHERE company_id = :company_id)
    """)
    inst_data = db.execute(inst_q, {"company_id": company_id}).mappings().first()

    insider_bullish = insider_data["buy_count"] > 0
    inst_bullish = (inst_data["net_inst_change"] or 0) > 0

    alignment_score = 0.0
    if insider_bullish:
        alignment_score += 5.0
    if inst_bullish:
        alignment_score += 5.0

    return {
        "ticker": ticker.upper(),
        "insider_buy_count_90d": insider_data["buy_count"],
        "insider_buy_value_90d": float(insider_data["buy_value"]),
        "inst_net_share_change": inst_data["net_inst_change"],
        "inst_buyers_last_quarter": inst_data["inst_buyers"],
        "insider_bullish": insider_bullish,
        "institutional_bullish": inst_bullish,
        "alignment_score": alignment_score,
    }
