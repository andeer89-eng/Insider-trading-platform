"""
FINTEL Institutional Holdings Pipeline
=======================================
Parses 13F quarterly filings from SEC EDGAR for major institutional investors.

13F filings are filed within 45 days of each quarter end.
Quarter ends: March 31, June 30, September 30, December 31
"""
import logging
import httpx
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Optional
from sqlalchemy import text

from models.database import SessionLocal

logger = logging.getLogger(__name__)

SEC_BASE = "https://data.sec.gov"
HEADERS = {"User-Agent": "FintelPlatform research@fintel.io"}

# 13F-HR XML namespace
NS_13F = {"ns": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}


def get_quarter_end(d: date) -> date:
    """Get the quarter-end date for a given date."""
    month = d.month
    if month <= 3:
        return date(d.year, 3, 31)
    elif month <= 6:
        return date(d.year, 6, 30)
    elif month <= 9:
        return date(d.year, 9, 30)
    else:
        return date(d.year, 12, 31)


def fetch_recent_13f(cik: str, n_quarters: int = 4) -> list:
    """Fetch recent 13F filing metadata for a firm."""
    cik_padded = cik.zfill(10)
    url = f"{SEC_BASE}/submissions/CIK{cik_padded}.json"

    try:
        resp = httpx.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        filing_dates = filings.get("filingDate", [])

        results = []
        for i, form in enumerate(forms):
            if form in ("13F-HR", "13F-HR/A") and len(results) < n_quarters:
                results.append({
                    "accession": accessions[i].replace("-", ""),
                    "filing_date": datetime.strptime(filing_dates[i], "%Y-%m-%d").date(),
                    "form_type": form,
                    "cik": cik_padded,
                })
        return results
    except Exception as e:
        logger.warning(f"Failed to fetch 13F filings for CIK {cik}: {e}")
        return []


def fetch_13f_xml(cik: str, accession: str) -> Optional[str]:
    """Download and return 13F information table XML."""
    url = f"{SEC_BASE}/Archives/edgar/data/{int(cik)}/{accession}/informationtable.xml"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.warning(f"Failed to download 13F XML: {cik}/{accession}: {e}")
        return None


def parse_13f_xml(xml_content: str) -> list:
    """
    Parse 13F information table XML.
    Returns list of holdings dicts.
    """
    holdings = []
    try:
        root = ET.fromstring(xml_content)

        for info in root.findall(".//ns:infoTable", NS_13F):
            def get(tag):
                el = info.find(f"ns:{tag}", NS_13F)
                return el.text.strip() if el is not None and el.text else None

            cusip = get("cusip")
            name = get("nameOfIssuer")
            value_str = get("value")          # in thousands
            shares_str = get("sshPrnamt")
            shares_type = get("sshPrnamtType")

            if not cusip or not value_str:
                continue

            try:
                value = int(value_str) * 1000  # convert from thousands to USD
                shares = int(shares_str) if shares_str else None
            except ValueError:
                continue

            holdings.append({
                "cusip": cusip,
                "name": name,
                "value": value,
                "shares": shares,
                "shares_type": shares_type,
            })
    except Exception as e:
        logger.warning(f"Failed to parse 13F XML: {e}")

    return holdings


def lookup_company_by_cusip_or_name(db, cusip: str, name: str) -> Optional[int]:
    """
    Try to match a 13F holding to a company in our database.
    Uses fuzzy name matching as CUSIP→ticker mapping would require paid data.
    """
    # Try name-based matching
    row = db.execute(text("""
        SELECT id FROM companies
        WHERE name ILIKE :name
           OR ticker = :ticker
        LIMIT 1
    """), {
        "name": f"%{name[:20]}%" if name else "",
        "ticker": name.split()[0][:5].upper() if name else "",
    }).fetchone()
    return row[0] if row else None


def ingest_13f(db, firm_id: int, filing_meta: dict) -> int:
    """Ingest a single 13F filing. Returns number of holdings processed."""
    xml_content = fetch_13f_xml(filing_meta["cik"], filing_meta["accession"])
    if not xml_content:
        return 0

    holdings = parse_13f_xml(xml_content)
    if not holdings:
        return 0

    quarter = get_quarter_end(filing_meta["filing_date"] - __import__("datetime").timedelta(days=45))
    count = 0

    for holding in holdings:
        company_id = lookup_company_by_cusip_or_name(db, holding["cusip"], holding["name"])
        if not company_id:
            continue

        # Get previous quarter's holding for change calculation
        prev_q = db.execute(text("""
            SELECT shares, value FROM institutional_holdings
            WHERE firm_id = :firm_id AND company_id = :company_id
              AND quarter < :quarter
            ORDER BY quarter DESC LIMIT 1
        """), {"firm_id": firm_id, "company_id": company_id, "quarter": quarter}).fetchone()

        prev_shares = prev_q[0] if prev_q else None
        change_shares = (holding["shares"] - prev_shares) if holding["shares"] and prev_shares else None
        change_pct = (change_shares / prev_shares * 100) if change_shares and prev_shares and prev_shares != 0 else None

        try:
            db.execute(text("""
                INSERT INTO institutional_holdings
                    (firm_id, company_id, quarter, shares, value,
                     shares_prev, value_prev, change_shares, change_pct,
                     filing_date, accession_number)
                VALUES
                    (:firm_id, :company_id, :quarter, :shares, :value,
                     :shares_prev, :value_prev, :change_shares, :change_pct,
                     :filing_date, :accession)
                ON CONFLICT (firm_id, company_id, quarter) DO UPDATE SET
                    shares = EXCLUDED.shares,
                    value = EXCLUDED.value,
                    change_shares = EXCLUDED.change_shares,
                    change_pct = EXCLUDED.change_pct
            """), {
                "firm_id": firm_id,
                "company_id": company_id,
                "quarter": quarter,
                "shares": holding["shares"],
                "value": holding["value"],
                "shares_prev": prev_shares,
                "value_prev": prev_q[1] if prev_q else None,
                "change_shares": change_shares,
                "change_pct": change_pct,
                "filing_date": filing_meta["filing_date"],
                "accession": filing_meta["accession"],
            })
            count += 1
        except Exception as e:
            logger.debug(f"Holdings insert error: {e}")

    return count


def run_institutional_pipeline():
    """Main 13F pipeline entry point."""
    db = SessionLocal()
    total = 0

    logger.info("Starting institutional 13F pipeline...")

    try:
        run_id = db.execute(text("""
            INSERT INTO pipeline_runs (pipeline, status)
            VALUES ('institutional_13f', 'running') RETURNING id
        """)).scalar()
        db.commit()

        firms = db.execute(text(
            "SELECT id, name, cik FROM institutional_firms WHERE cik IS NOT NULL"
        )).fetchall()

        for firm_id, firm_name, cik in firms:
            logger.info(f"Processing 13F for: {firm_name}")
            filings = fetch_recent_13f(cik, n_quarters=2)

            for filing_meta in filings:
                count = ingest_13f(db, firm_id, filing_meta)
                total += count
                if count > 0:
                    db.commit()
                    logger.info(f"  Ingested {count} holdings from {filing_meta['accession']}")

        db.execute(text("""
            UPDATE pipeline_runs SET status='success', ended_at=NOW(), records_processed=:n
            WHERE id=:id
        """), {"n": total, "id": run_id})
        db.commit()

        logger.info(f"Institutional pipeline complete: {total} holdings ingested")

    except Exception as e:
        logger.error(f"Institutional pipeline failed: {e}")
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
