"""
AI Analyst — Natural language query interface over the FINTEL database.
Users ask plain-English questions; GPT-4o translates them to safe SQL,
executes against the read-only DB, then explains the results.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Any, Optional
import os
import re
import json
import logging

from models.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Schema context fed to GPT-4o so it can write accurate SQL
# ---------------------------------------------------------------------------
DB_SCHEMA_CONTEXT = """
You are a SQL expert for the FINTEL financial intelligence platform (PostgreSQL).

DATABASE TABLES:

companies (id, ticker, name, sector, industry, market_cap, exchange, cik)
  - S&P 500 companies. sector values: 'Technology', 'Healthcare', 'Financials',
    'Consumer Discretionary', 'Communication Services', 'Industrials',
    'Consumer Staples', 'Energy', 'Materials', 'Real Estate', 'Utilities'

insiders (id, company_id, name, role, cik)
  - role values: 'CEO', 'CFO', 'COO', 'CTO', 'President', 'Director',
    'VP', '10% Owner', 'Chairman'

insider_transactions (id, company_id, insider_id, transaction_date DATE,
    transaction_type VARCHAR, shares NUMERIC, price NUMERIC,
    transaction_value NUMERIC, ownership_change_pct NUMERIC,
    filing_type VARCHAR, filing_url TEXT)
  - transaction_type: 'Buy', 'Purchase', 'Sell', 'Award', 'Exercise'

insider_signal_scores (id, transaction_id, score NUMERIC 0-10,
    size_score, role_score, history_score, ownership_score, cluster_flag BOOLEAN,
    insider_skill_score NUMERIC, signal_reason TEXT, scored_at TIMESTAMP)
  - score >= 7 = high conviction, 5-7 = moderate, < 5 = low

insider_trade_outcomes (id, transaction_id, return_7d, return_30d,
    return_90d, return_1y, return_2y, alpha_vs_sp500_30d, alpha_vs_sp500_90d,
    alpha_vs_sp500_1y, calculated_at TIMESTAMP)

insider_cluster_events (id, company_id, start_date DATE, end_date DATE,
    insider_count INT, total_shares NUMERIC, total_value NUMERIC,
    unique_roles TEXT[], cluster_score NUMERIC)
  - Multiple insiders buying same company within 14-day window

institutional_firms (id, name, firm_type, cik)
  - firm_type: 'Hedge Fund', 'Mutual Fund', 'Pension Fund', 'Investment Advisor'

institutional_holdings (id, company_id, firm_id, quarter DATE,
    shares NUMERIC, value NUMERIC, change_shares NUMERIC, change_pct NUMERIC,
    is_new_position BOOLEAN, is_closed_position BOOLEAN)

company_composite_scores (id, company_id, date DATE, insider_score NUMERIC,
    institutional_score NUMERIC, business_momentum_score NUMERIC,
    industry_score NUMERIC, composite_score NUMERIC, insider_alignment NUMERIC)

company_metric_values (id, company_id, metric_id, date DATE,
    value NUMERIC, yoy_growth NUMERIC, source VARCHAR, confidence NUMERIC)

metrics (id, name, display_name, category, subcategory, unit,
    description, frequency)
  - category: 'financial', 'operational', 'user_metrics', 'infrastructure'

stock_prices (id, company_id, date DATE, open, high, low, close NUMERIC,
    volume BIGINT, adjusted_close NUMERIC)

USEFUL JOINS:
- insider_transactions → companies: JOIN companies c ON c.id = it.company_id
- insider_transactions → insiders: JOIN insiders i ON i.id = it.insider_id
- insider_transactions → signal scores: JOIN insider_signal_scores iss ON iss.transaction_id = it.id
- company_metric_values → metrics: JOIN metrics m ON m.id = cmv.metric_id
- company_metric_values → companies: JOIN companies c ON c.id = cmv.company_id

IMPORTANT RULES:
1. Only write SELECT queries — never INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE.
2. Always add LIMIT (max 200 rows) unless COUNT/SUM/AVG aggregate.
3. Use ILIKE for case-insensitive text matching on names/tickers.
4. For "recent" or "latest" use ORDER BY date DESC with appropriate LIMIT.
5. Return only the SQL query, nothing else — no markdown, no explanation.
"""

EXAMPLE_QUESTIONS = [
    "Which CEOs bought the most stock in the last 30 days?",
    "Show me the top 10 companies by composite opportunity score in the Technology sector",
    "What are the highest-conviction insider buy signals (score >= 8) this quarter?",
    "Which companies had cluster buying events (multiple insiders buying) this month?",
    "Show average signal score by insider role",
    "What are NVIDIA's latest operational metrics?",
    "Which sectors have the most insider buying activity in the last 90 days?",
    "Show me the top institutional accumulators of Tesla stock",
    "What is the average 90-day return after high-conviction insider buys (score >= 7)?",
    "List companies where both insiders and institutions are aggressively buying",
]

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AnalystQuery(BaseModel):
    question: str


class ColumnMeta(BaseModel):
    name: str
    type: str


class AnalystResult(BaseModel):
    question: str
    sql: str
    columns: list[ColumnMeta]
    rows: list[dict[str, Any]]
    row_count: int
    explanation: str
    truncated: bool


# ---------------------------------------------------------------------------
# Safety validator — ensures only read-only SQL runs
# ---------------------------------------------------------------------------
_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE"
    r"|EXECUTE|EXEC|CALL|COPY|VACUUM|ANALYZE|EXPLAIN\s+ANALYZE"
    r"|pg_sleep|pg_read_file|pg_ls_dir|lo_import|lo_export)\b",
    re.IGNORECASE,
)
_MUST_SELECT = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
_MAX_ROWS = 200


def validate_sql(sql: str) -> str:
    """Raise ValueError if the SQL is not a safe read-only SELECT."""
    clean = sql.strip().rstrip(";")
    if not _MUST_SELECT.match(clean):
        raise ValueError("Only SELECT queries are permitted.")
    if _FORBIDDEN.search(clean):
        raise ValueError("Query contains forbidden SQL keywords.")
    # Inject LIMIT if not present and not an aggregate-only query
    if not re.search(r"\bLIMIT\b", clean, re.IGNORECASE):
        agg_only = re.search(r"^\s*SELECT\s+(COUNT|SUM|AVG|MIN|MAX)\s*\(", clean, re.IGNORECASE)
        if not agg_only:
            clean = f"{clean} LIMIT {_MAX_ROWS}"
    return clean


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------

def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured. Set it in your environment.",
        )
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def generate_sql(question: str) -> str:
    """Use GPT-4o to translate a natural language question into SQL."""
    client = _get_openai_client()
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": DB_SCHEMA_CONTEXT},
            {"role": "user", "content": f"Question: {question}\n\nWrite a PostgreSQL SELECT query to answer this."},
        ],
        temperature=0,
        max_tokens=800,
    )
    raw = resp.choices[0].message.content or ""
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:sql)?\s*", "", raw).strip().strip("`").strip()
    return raw


def explain_results(question: str, sql: str, rows: list[dict], truncated: bool) -> str:
    """Use GPT-4o to write a concise plain-English explanation of the query results."""
    client = _get_openai_client()
    sample = rows[:10]
    truncation_note = f" (showing first {_MAX_ROWS} of more rows)" if truncated else ""
    prompt = (
        f"The user asked: \"{question}\"\n\n"
        f"The SQL executed:\n{sql}\n\n"
        f"Results ({len(rows)} rows{truncation_note}):\n{json.dumps(sample, indent=2, default=str)}\n\n"
        "Write a concise 2-4 sentence plain-English summary of what these results show. "
        "Highlight the most important findings. Do not repeat the SQL."
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a financial data analyst summarizing query results for investors."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=300,
    )
    return (resp.choices[0].message.content or "").strip()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/query", response_model=AnalystResult)
def analyst_query(payload: AnalystQuery, db: Session = Depends(get_db)):
    """
    Accept a natural-language question, generate + execute safe SQL,
    and return data with an AI-written explanation.
    """
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if len(question) > 500:
        raise HTTPException(status_code=400, detail="Question too long (max 500 characters).")

    # 1. Generate SQL
    try:
        raw_sql = generate_sql(question)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("SQL generation failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"AI generation failed: {exc}")

    # 2. Validate SQL safety
    try:
        safe_sql = validate_sql(raw_sql)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Generated query failed safety check: {exc}")

    # 3. Execute in a read-only transaction (rolled back after)
    try:
        with db.begin_nested():
            result = db.execute(text(safe_sql))
            col_names = list(result.keys())
            raw_rows = result.fetchall()
    except Exception as exc:
        logger.error("SQL execution error: %s | SQL: %s", exc, safe_sql)
        raise HTTPException(status_code=422, detail=f"Query execution error: {exc}")

    truncated = len(raw_rows) >= _MAX_ROWS
    rows = [dict(zip(col_names, row)) for row in raw_rows]

    # Serialise non-JSON-native types
    for row in rows:
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                row[k] = v.isoformat()
            elif isinstance(v, (list,)):
                row[k] = [str(x) for x in v]

    # 4. Explain results
    try:
        explanation = explain_results(question, safe_sql, rows, truncated)
    except Exception as exc:
        logger.warning("Explanation generation failed: %s", exc)
        explanation = f"Query returned {len(rows)} row(s)."

    columns = [ColumnMeta(name=c, type="text") for c in col_names]

    return AnalystResult(
        question=question,
        sql=safe_sql,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        explanation=explanation,
        truncated=truncated,
    )


@router.get("/examples")
def get_examples():
    """Return example questions to help users get started."""
    return {"examples": EXAMPLE_QUESTIONS}
