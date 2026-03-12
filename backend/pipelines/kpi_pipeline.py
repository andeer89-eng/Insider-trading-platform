"""
FINTEL KPI Extraction Pipeline
================================
Extracts operational KPIs from earnings transcripts and 10-K filings.
Uses LLM (OpenAI GPT) to identify and normalize metric values.

Pipeline:
  1. Collect earnings transcripts (from SEC EDGAR or third-party)
  2. Chunk text into manageable segments
  3. Run LLM extraction prompt
  4. Normalize metric names against metric registry
  5. Store in company_metric_values
"""
import logging
import json
import re
from datetime import date
from typing import Optional
from sqlalchemy import text

from models.database import SessionLocal

logger = logging.getLogger(__name__)

# LLM extraction prompt template
EXTRACTION_PROMPT = """
You are a financial analyst extracting operational KPIs from an earnings call transcript or 10-K filing.

Company: {company_name} ({ticker})
Period: {period}

TRANSCRIPT EXCERPT:
---
{text}
---

Extract every quantitative metric mentioned. For each metric:
1. Identify the metric name (use snake_case)
2. Extract the numeric value
3. Identify the unit (count, $M, $B, GWh, MW, %, etc.)
4. Identify the period (quarterly, annual, monthly)

Return a JSON array of objects with this schema:
[
  {{
    "metric_name": "supercharger_sites",
    "display_name": "Supercharger Sites",
    "value": 50000,
    "unit": "count",
    "period": "quarterly",
    "category": "infrastructure",
    "context": "quote or phrase from transcript"
  }}
]

Focus on operational metrics specific to this company's business:
- Physical infrastructure (stores, stations, datacenters, factories)
- Production/shipment volumes
- User/subscriber counts
- Key product adoption metrics
- Service revenue and growth rates

Return ONLY the JSON array, no other text.
"""


def extract_kpis_with_llm(
    text_chunk: str,
    company_name: str,
    ticker: str,
    period: str,
) -> list:
    """Use OpenAI to extract KPIs from text."""
    try:
        import openai
        import os

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        prompt = EXTRACTION_PROMPT.format(
            company_name=company_name,
            ticker=ticker,
            period=period,
            text=text_chunk[:4000],
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        # Handle both array and object with array key
        if isinstance(data, list):
            return data
        for key in ["metrics", "kpis", "results", "data"]:
            if key in data:
                return data[key]
        return []

    except Exception as e:
        logger.warning(f"LLM extraction failed: {e}")
        return []


def normalize_value(value_str) -> Optional[float]:
    """Convert string value to float (handles B/M/K suffixes)."""
    if value_str is None:
        return None
    if isinstance(value_str, (int, float)):
        return float(value_str)

    v = str(value_str).strip().replace(",", "").replace("$", "")
    multipliers = {"B": 1e9, "M": 1e6, "K": 1e3, "T": 1e12}
    for suffix, mult in multipliers.items():
        if v.upper().endswith(suffix):
            try:
                return float(v[:-1]) * mult
            except ValueError:
                return None
    try:
        return float(v)
    except ValueError:
        return None


def get_or_create_metric(db, metric_name: str, display_name: str, category: str, unit: str) -> int:
    """Get or create a metric in the registry."""
    row = db.execute(
        text("SELECT id FROM metrics WHERE name = :name"),
        {"name": metric_name}
    ).fetchone()
    if row:
        return row[0]

    row = db.execute(text("""
        INSERT INTO metrics (name, display_name, category, unit, source, frequency)
        VALUES (:name, :display_name, :category, :unit, 'ai_extracted', 'quarterly')
        RETURNING id
    """), {
        "name": metric_name,
        "display_name": display_name or metric_name.replace("_", " ").title(),
        "category": category or "operational",
        "unit": unit,
    }).fetchone()
    return row[0]


def process_transcript(db, transcript_id: int, company_id: int, ticker: str,
                       company_name: str, fiscal_quarter: str, text_content: str) -> int:
    """Process a single earnings transcript and extract KPIs."""
    count = 0

    # Chunk transcript into ~2000 word segments
    words = text_content.split()
    chunk_size = 2000
    chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

    all_kpis = []
    for chunk in chunks[:5]:  # Process max 5 chunks per transcript
        kpis = extract_kpis_with_llm(chunk, company_name, ticker, fiscal_quarter)
        all_kpis.extend(kpis)

    # Deduplicate by metric name
    seen = set()
    unique_kpis = []
    for kpi in all_kpis:
        if kpi.get("metric_name") not in seen:
            seen.add(kpi["metric_name"])
            unique_kpis.append(kpi)

    # Store each KPI
    for kpi in unique_kpis:
        metric_name = kpi.get("metric_name")
        if not metric_name:
            continue

        value = normalize_value(kpi.get("value"))
        if value is None:
            continue

        metric_id = get_or_create_metric(
            db,
            metric_name=metric_name,
            display_name=kpi.get("display_name", ""),
            category=kpi.get("category", "operational"),
            unit=kpi.get("unit", ""),
        )

        # Parse date from fiscal_quarter (e.g., "Q1 2024" → 2024-03-31)
        period_date = parse_fiscal_quarter_date(fiscal_quarter)

        try:
            db.execute(text("""
                INSERT INTO company_metric_values
                    (company_id, metric_id, date, value, source, confidence_score)
                VALUES
                    (:company_id, :metric_id, :date, :value, 'ai_extracted', 0.8)
                ON CONFLICT (company_id, metric_id, date) DO NOTHING
            """), {
                "company_id": company_id,
                "metric_id": metric_id,
                "date": period_date,
                "value": value,
            })
            count += 1
        except Exception as e:
            logger.debug(f"KPI insert error: {e}")

    # Mark transcript as processed
    db.execute(text("""
        UPDATE earnings_transcripts SET processed = TRUE WHERE id = :id
    """), {"id": transcript_id})

    return count


def parse_fiscal_quarter_date(quarter_str: str) -> date:
    """Convert 'Q1 2024' → 2024-03-31, 'Q2 2024' → 2024-06-30, etc."""
    try:
        parts = quarter_str.upper().split()
        q_num = int(parts[0].replace("Q", ""))
        year = int(parts[1])
        month_map = {1: 3, 2: 6, 3: 9, 4: 12}
        month = month_map.get(q_num, 12)
        from calendar import monthrange
        last_day = monthrange(year, month)[1]
        return date(year, month, last_day)
    except Exception:
        return date.today()


def run_kpi_pipeline():
    """Main KPI extraction pipeline entry point."""
    db = SessionLocal()
    total = 0

    logger.info("Starting KPI extraction pipeline...")

    try:
        run_id = db.execute(text("""
            INSERT INTO pipeline_runs (pipeline, status)
            VALUES ('kpi_extraction', 'running') RETURNING id
        """)).scalar()
        db.commit()

        # Get unprocessed transcripts
        transcripts = db.execute(text("""
            SELECT et.id, et.company_id, et.fiscal_quarter, et.raw_text,
                   c.ticker, c.name AS company_name
            FROM earnings_transcripts et
            JOIN companies c ON c.id = et.company_id
            WHERE et.processed = FALSE
              AND et.raw_text IS NOT NULL
              AND et.raw_text != ''
            LIMIT 50
        """)).mappings().fetchall()

        logger.info(f"Processing {len(transcripts)} unprocessed transcripts")

        for t in transcripts:
            try:
                count = process_transcript(
                    db=db,
                    transcript_id=t["id"],
                    company_id=t["company_id"],
                    ticker=t["ticker"],
                    company_name=t["company_name"],
                    fiscal_quarter=t["fiscal_quarter"] or "Q4 2024",
                    text_content=t["raw_text"],
                )
                total += count
                db.commit()
                logger.info(f"  {t['ticker']}: Extracted {count} KPIs")
            except Exception as e:
                logger.error(f"  Error processing transcript {t['id']}: {e}")
                db.rollback()

        db.execute(text("""
            UPDATE pipeline_runs SET status='success', ended_at=NOW(), records_processed=:n
            WHERE id=:id
        """), {"n": total, "id": run_id})
        db.commit()

        logger.info(f"KPI pipeline complete: {total} metrics extracted")

    except Exception as e:
        logger.error(f"KPI pipeline failed: {e}")
        try:
            db.execute(text("""
                UPDATE pipeline_runs SET status='failed', ended_at=NOW(), error_message=:err
                WHERE id=:id
            """), {"err": str(e), "id": run_id})
            db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()

    return total
