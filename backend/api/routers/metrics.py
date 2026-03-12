"""
Metrics registry and time-series endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional

from models.database import get_db
from models.schemas import MetricDef, CompanyMetricSeries, MetricComparison, MetricValue, MetricComparisonItem

router = APIRouter()


@router.get("", response_model=List[MetricDef])
def list_metrics(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all metrics in the registry."""
    conditions = ["1=1"]
    params: dict = {}

    if category:
        conditions.append("category = :category")
        params["category"] = category

    where = " AND ".join(conditions)
    q = text(f"SELECT * FROM metrics WHERE {where} ORDER BY category, name")
    rows = db.execute(q, params).mappings().all()
    return [MetricDef(**dict(r)) for r in rows]


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    """List all metric categories."""
    q = text("SELECT DISTINCT category FROM metrics ORDER BY category")
    rows = db.execute(q).fetchall()
    return [r[0] for r in rows]


@router.get("/{metric_name}/compare", response_model=MetricComparison)
def compare_metric(
    metric_name: str,
    tickers: str = Query(..., description="Comma-separated tickers, e.g. NVDA,AMD,INTC"),
    limit_years: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Compare a specific metric across multiple companies.
    Returns time-series for each company — powers the cross-company comparison charts.
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]

    # Get metric definition
    metric_q = text("SELECT * FROM metrics WHERE name = :name")
    metric_row = db.execute(metric_q, {"name": metric_name}).mappings().first()
    if not metric_row:
        raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found")

    metric = MetricDef(**dict(metric_row))

    # Get companies
    companies_q = text("SELECT id, ticker, name FROM companies WHERE ticker = ANY(:tickers)")
    companies = db.execute(companies_q, {"tickers": ticker_list}).mappings().all()

    result_companies = []
    for company in companies:
        values_q = text("""
            SELECT date, value, yoy_growth, source, confidence_score
            FROM company_metric_values
            WHERE company_id = :company_id
              AND metric_id = :metric_id
              AND date >= CURRENT_DATE - INTERVAL ':years years'
            ORDER BY date
        """.replace(":years", str(limit_years)))
        values = db.execute(values_q, {
            "company_id": company["id"],
            "metric_id": metric.id,
        }).mappings().all()

        result_companies.append(MetricComparisonItem(
            company_id=company["id"],
            ticker=company["ticker"],
            company_name=company["name"],
            values=[MetricValue(**dict(v)) for v in values],
        ))

    return MetricComparison(metric=metric, companies=result_companies)


@router.get("/company/{ticker}", response_model=List[dict])
def get_company_metrics(
    ticker: str,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get all metrics for a company, with latest values."""
    company_q = text("SELECT id FROM companies WHERE ticker = :ticker")
    company = db.execute(company_q, {"ticker": ticker.upper()}).fetchone()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    conditions = ["cmv.company_id = :company_id"]
    params: dict = {"company_id": company[0]}

    if category:
        conditions.append("m.category = :category")
        params["category"] = category

    where = " AND ".join(conditions)
    q = text(f"""
        SELECT DISTINCT ON (cmv.metric_id)
            m.id AS metric_id,
            m.name AS metric_name,
            m.display_name,
            m.category,
            m.subcategory,
            m.unit,
            cmv.date,
            cmv.value,
            cmv.yoy_growth,
            cmv.source
        FROM company_metric_values cmv
        JOIN metrics m ON m.id = cmv.metric_id
        WHERE {where}
        ORDER BY cmv.metric_id, cmv.date DESC
    """)
    rows = db.execute(q, params).mappings().all()
    return [dict(r) for r in rows]


@router.get("/company/{ticker}/{metric_name}/series")
def get_metric_series(
    ticker: str,
    metric_name: str,
    limit_years: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Time-series for a specific metric for a company."""
    q = text("""
        SELECT cmv.date, cmv.value, cmv.yoy_growth, cmv.source, cmv.confidence_score
        FROM company_metric_values cmv
        JOIN companies c ON c.id = cmv.company_id
        JOIN metrics m ON m.id = cmv.metric_id
        WHERE c.ticker = :ticker
          AND m.name = :metric_name
          AND cmv.date >= CURRENT_DATE - (:years || ' years')::INTERVAL
        ORDER BY cmv.date
    """)
    rows = db.execute(q, {
        "ticker": ticker.upper(),
        "metric_name": metric_name,
        "years": limit_years,
    }).mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail="No data found for this metric/company combination")

    return [dict(r) for r in rows]


@router.get("/industry/{industry_name}")
def get_industry_metrics(
    industry_name: str,
    metric_name: str = Query(...),
    db: Session = Depends(get_db),
):
    """Get a metric for all companies in an industry."""
    q = text("""
        SELECT DISTINCT ON (cmv.company_id)
            c.ticker, c.name AS company_name,
            cmv.date, cmv.value, cmv.yoy_growth
        FROM company_metric_values cmv
        JOIN companies c ON c.id = cmv.company_id
        JOIN metrics m ON m.id = cmv.metric_id
        WHERE c.industry = :industry
          AND m.name = :metric_name
        ORDER BY cmv.company_id, cmv.date DESC
    """)
    rows = db.execute(q, {"industry": industry_name, "metric_name": metric_name}).mappings().all()
    return [dict(r) for r in rows]
