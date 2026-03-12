"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


# ============================================================
# COMPANY SCHEMAS
# ============================================================
class CompanyBase(BaseModel):
    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[int] = None

class CompanySummary(CompanyBase):
    id: int
    exchange: Optional[str] = None
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True

class CompanyDetail(CompanySummary):
    cik: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    ipo_date: Optional[date] = None
    composite_score: Optional[float] = None
    insider_score: Optional[float] = None
    institutional_score: Optional[float] = None
    business_momentum_score: Optional[float] = None

    class Config:
        from_attributes = True


# ============================================================
# INSIDER SCHEMAS
# ============================================================
class InsiderBase(BaseModel):
    name: str
    role: Optional[str] = None
    is_officer: bool = False
    is_director: bool = False

class InsiderSummary(InsiderBase):
    id: int
    company_id: int

    class Config:
        from_attributes = True

class InsiderWithStats(InsiderSummary):
    total_trades: Optional[int] = None
    total_buys: Optional[int] = None
    total_sells: Optional[int] = None
    avg_alpha_30d: Optional[float] = None
    skill_score: Optional[float] = None


# ============================================================
# TRANSACTION SCHEMAS
# ============================================================
class InsiderTransactionBase(BaseModel):
    transaction_date: date
    transaction_type: str
    shares: Decimal
    price: Optional[Decimal] = None
    transaction_value: Optional[Decimal] = None
    ownership_before: Optional[Decimal] = None
    ownership_after: Optional[Decimal] = None
    ownership_change_pct: Optional[Decimal] = None
    filing_type: Optional[str] = None
    filing_url: Optional[str] = None

class InsiderTransactionSummary(InsiderTransactionBase):
    id: int
    company_id: int
    insider_id: Optional[int] = None
    insider_name: Optional[str] = None
    insider_role: Optional[str] = None
    ticker: Optional[str] = None
    company_name: Optional[str] = None
    signal_score: Optional[float] = None
    cluster_flag: Optional[bool] = None

    class Config:
        from_attributes = True

class InsiderTransactionDetail(InsiderTransactionSummary):
    filing_date: Optional[date] = None
    accession_number: Optional[str] = None
    security_title: Optional[str] = None
    is_direct: Optional[bool] = None
    footnote: Optional[str] = None
    return_7d: Optional[float] = None
    return_30d: Optional[float] = None
    return_90d: Optional[float] = None
    return_1y: Optional[float] = None


# ============================================================
# SIGNAL SCHEMAS
# ============================================================
class InsiderSignalScore(BaseModel):
    transaction_id: int
    score: float = Field(..., ge=0, le=10)
    size_score: Optional[float] = None
    role_score: Optional[float] = None
    history_score: Optional[float] = None
    ownership_score: Optional[float] = None
    cluster_flag: bool = False
    ownership_change_pct: Optional[float] = None
    insider_skill_score: Optional[float] = None
    signal_reason: Optional[str] = None

    class Config:
        from_attributes = True

class TopInsiderSignal(BaseModel):
    transaction_id: int
    ticker: str
    company_name: str
    sector: Optional[str] = None
    insider_name: Optional[str] = None
    insider_role: Optional[str] = None
    transaction_date: date
    transaction_type: str
    shares: Decimal
    price: Optional[Decimal] = None
    transaction_value: Optional[Decimal] = None
    ownership_change_pct: Optional[Decimal] = None
    signal_score: Optional[float] = None
    cluster_flag: Optional[bool] = None
    insider_skill_score: Optional[float] = None
    signal_reason: Optional[str] = None


# ============================================================
# METRIC SCHEMAS
# ============================================================
class MetricDef(BaseModel):
    id: int
    name: str
    display_name: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    frequency: Optional[str] = None

    class Config:
        from_attributes = True

class MetricValue(BaseModel):
    date: date
    value: Optional[float] = None
    yoy_growth: Optional[float] = None
    source: Optional[str] = None
    confidence_score: Optional[float] = None

    class Config:
        from_attributes = True

class CompanyMetricSeries(BaseModel):
    company_id: int
    ticker: str
    company_name: str
    metric: MetricDef
    values: List[MetricValue]

class MetricComparisonItem(BaseModel):
    company_id: int
    ticker: str
    company_name: str
    values: List[MetricValue]

class MetricComparison(BaseModel):
    metric: MetricDef
    companies: List[MetricComparisonItem]


# ============================================================
# COMPOSITE SCORE SCHEMAS
# ============================================================
class CompositeScore(BaseModel):
    company_id: int
    ticker: str
    company_name: str
    sector: Optional[str] = None
    date: date
    insider_score: Optional[float] = None
    institutional_score: Optional[float] = None
    business_momentum_score: Optional[float] = None
    industry_score: Optional[float] = None
    composite_score: Optional[float] = None
    insider_alignment: Optional[float] = None

    class Config:
        from_attributes = True


# ============================================================
# INSTITUTIONAL HOLDING SCHEMAS
# ============================================================
class InstitutionalHoldingSummary(BaseModel):
    firm_name: str
    firm_type: Optional[str] = None
    quarter: date
    shares: Optional[int] = None
    value: Optional[int] = None
    change_shares: Optional[int] = None
    change_pct: Optional[float] = None

    class Config:
        from_attributes = True

class CompanyOwnership(BaseModel):
    company_id: int
    ticker: str
    total_institutional_shares: Optional[int] = None
    institutional_ownership_pct: Optional[float] = None
    num_holders: Optional[int] = None
    top_holders: List[InstitutionalHoldingSummary] = []
    net_change_last_quarter: Optional[int] = None
    accumulation_score: Optional[float] = None


# ============================================================
# CLUSTER EVENT SCHEMAS
# ============================================================
class ClusterEvent(BaseModel):
    id: int
    company_id: int
    ticker: str
    company_name: str
    start_date: date
    end_date: date
    insider_count: int
    total_value: Optional[float] = None
    unique_roles: Optional[List[str]] = None
    cluster_score: Optional[float] = None

    class Config:
        from_attributes = True


# ============================================================
# DASHBOARD / HOMEPAGE SCHEMAS
# ============================================================
class HomepageData(BaseModel):
    top_signals: List[TopInsiderSignal]
    top_composite_scores: List[CompositeScore]
    recent_cluster_events: List[ClusterEvent]
    total_transactions_today: int
    total_buy_value_today: float
    market_date: date

class PipelineStatus(BaseModel):
    pipeline: str
    status: str
    last_run: Optional[datetime] = None
    records_processed: Optional[int] = None
    error: Optional[str] = None
