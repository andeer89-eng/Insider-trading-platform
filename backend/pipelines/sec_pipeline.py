"""
FINTEL SEC Filing Pipeline
==========================
Ingests Form 3, 4, 5 insider transaction filings from SEC EDGAR.
Uses the official EDGAR full-text search API + XBRL facts.

Pipeline stages:
  1. Fetch recent Form 4 filings from EDGAR submissions API
  2. Parse XML transaction data
  3. Normalize insiders and companies
  4. Upsert to insider_transactions table
  5. Trigger signal scoring

Documentation: https://www.sec.gov/developer
"""
import logging
import time
import httpx
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy import text

from models.database import SessionLocal

logger = logging.getLogger(__name__)

SEC_BASE = "https://data.sec.gov"
SEC_SUBMISSIONS = f"{SEC_BASE}/submissions"
SEC_FULL_TEXT = "https://efts.sec.gov/LATEST/search-index"
HEADERS = {"User-Agent": "FintelPlatform research@fintel.io"}

# Transaction type normalization
TX_TYPE_MAP = {
    "P": "Buy",        # Open market purchase
    "S": "Sell",       # Open market sale
    "A": "Award",      # Grant/award from company
    "D": "Disposition",
    "F": "Tax Withholding",
    "G": "Gift",
    "I": "Discretionary",
    "M": "Exercise",
    "C": "Convert",
    "E": "Expire",
    "H": "Return",
    "L": "Sell (short)",
    "W": "Acquired by will",
    "X": "Exercise or conversion",
    "Z": "Trust",
    "J": "Other",
    "K": "Equity swap",
    "U": "Tender offer",
}


def get_company_cik(ticker: str, db) -> Optional[str]:
    """Get SEC CIK for a ticker from our database."""
    row = db.execute(
        text("SELECT cik FROM companies WHERE ticker = :ticker"),
        {"ticker": ticker}
    ).fetchone()
    return row[0] if row and row[0] else None


def fetch_recent_form4_filings(cik: str, days_back: int = 7) -> list:
    """
    Fetch recent Form 4 filing metadata for a company from EDGAR.
    """
    cik_padded = cik.zfill(10)
    url = f"{SEC_SUBMISSIONS}/CIK{cik_padded}.json"

    try:
        resp = httpx.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        filing_dates = filings.get("filingDate", [])

        cutoff = date.today() - timedelta(days=days_back)
        form4_filings = []

        for i, form in enumerate(forms):
            if form in ("4", "4/A"):
                filing_date = datetime.strptime(filing_dates[i], "%Y-%m-%d").date()
                if filing_date >= cutoff:
                    form4_filings.append({
                        "accession": accessions[i].replace("-", ""),
                        "filing_date": filing_date,
                        "form_type": form,
                        "cik": cik_padded,
                    })

        return form4_filings
    except Exception as e:
        logger.warning(f"Failed to fetch filings for CIK {cik}: {e}")
        return []


def fetch_form4_xml(cik: str, accession: str) -> Optional[str]:
    """Download and return Form 4 XML content."""
    accession_formatted = f"{accession[:10]}-{accession[10:12]}-{accession[12:]}"
    url = f"{SEC_BASE}/Archives/edgar/data/{int(cik)}/{accession}/{accession_formatted}.txt"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        # Try alternative URL patterns
        try:
            url2 = f"{SEC_BASE}/Archives/edgar/data/{int(cik)}/{accession}/form4.xml"
            resp = httpx.get(url2, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.text
        except Exception:
            logger.warning(f"Could not download Form 4: {cik}/{accession}: {e}")
            return None


def parse_form4_xml(xml_content: str) -> Optional[dict]:
    """
    Parse Form 4 XML and extract transaction data.
    Returns structured dict with issuer, reporter, and transactions.
    """
    try:
        # Extract XML from SGML wrapper if needed
        if "<XML>" in xml_content:
            start = xml_content.index("<XML>") + 5
            end = xml_content.index("</XML>")
            xml_content = xml_content[start:end].strip()

        root = ET.fromstring(xml_content)
        ns = ""  # Form 4 XML has no namespace typically

        def get(tag):
            el = root.find(f".//{tag}")
            return el.text.strip() if el is not None and el.text else None

        # Issuer info
        issuer = {
            "cik": get("issuerCik"),
            "name": get("issuerName"),
            "ticker": get("issuerTradingSymbol"),
        }

        # Reporter (insider) info
        reporter = {
            "cik": get("rptOwnerCik"),
            "name": get("rptOwnerName"),
            "is_officer": get("isOfficer") == "1",
            "is_director": get("isDirector") == "1",
            "is_ten_pct": get("isTenPercentOwner") == "1",
            "role": get("officerTitle"),
        }

        # Non-derivative transactions (open market trades)
        transactions = []
        for tx_el in root.findall(".//nonDerivativeTransaction"):
            def txget(tag):
                el = tx_el.find(tag)
                return el.text.strip() if el is not None and el.text else None

            tx_code = txget("transactionCode")
            tx_type = TX_TYPE_MAP.get(tx_code, tx_code)

            shares_str = txget("transactionShares")
            price_str = txget("transactionPricePerShare")
            ownership_type = txget("directOrIndirectOwnership")

            # Post-transaction shares
            post_shares_str = txget("sharesOwnedFollowingTransaction")

            try:
                shares = float(shares_str) if shares_str else None
                price = float(price_str) if price_str else None
                post_shares = float(post_shares_str) if post_shares_str else None
            except ValueError:
                continue

            tx_value = (shares * price) if shares and price else None
            tx_date_str = txget("transactionDate")
            if not tx_date_str:
                continue

            try:
                tx_date = datetime.strptime(tx_date_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            transactions.append({
                "transaction_date": tx_date,
                "transaction_type": tx_type,
                "shares": shares,
                "price": price,
                "transaction_value": tx_value,
                "ownership_after": post_shares,
                "is_direct": ownership_type == "D",
                "security_title": txget("securityTitle"),
            })

        # Derivative transactions (options, warrants)
        for tx_el in root.findall(".//derivativeTransaction"):
            def txget(tag):
                el = tx_el.find(tag)
                return el.text.strip() if el is not None and el.text else None

            tx_code = txget("transactionCode")
            tx_type = TX_TYPE_MAP.get(tx_code, tx_code)
            tx_date_str = txget("transactionDate")
            if not tx_date_str:
                continue
            try:
                tx_date = datetime.strptime(tx_date_str, "%Y-%m-%d").date()
                shares = float(txget("transactionShares") or 0)
                price = float(txget("exercisePrice") or 0) or None
            except (ValueError, TypeError):
                continue

            transactions.append({
                "transaction_date": tx_date,
                "transaction_type": f"{tx_type} (Derivative)",
                "shares": shares,
                "price": price,
                "transaction_value": None,
                "ownership_after": None,
                "is_direct": True,
                "security_title": txget("securityTitle"),
            })

        return {
            "issuer": issuer,
            "reporter": reporter,
            "transactions": transactions,
        }

    except Exception as e:
        logger.warning(f"Failed to parse Form 4 XML: {e}")
        return None


def upsert_company(db, cik: str, ticker: str, name: str) -> Optional[int]:
    """Get or create company record."""
    row = db.execute(
        text("SELECT id FROM companies WHERE ticker = :ticker"),
        {"ticker": ticker.upper()}
    ).fetchone()
    if row:
        return row[0]

    row = db.execute(text("""
        INSERT INTO companies (ticker, name, cik)
        VALUES (:ticker, :name, :cik)
        ON CONFLICT (ticker) DO UPDATE SET name = EXCLUDED.name, cik = EXCLUDED.cik
        RETURNING id
    """), {"ticker": ticker.upper(), "name": name, "cik": cik}).fetchone()
    return row[0] if row else None


def upsert_insider(db, reporter: dict, company_id: int) -> Optional[int]:
    """Get or create insider record."""
    row = db.execute(text("""
        SELECT id FROM insiders
        WHERE name = :name AND company_id = :company_id
    """), {"name": reporter["name"], "company_id": company_id}).fetchone()

    if row:
        return row[0]

    row = db.execute(text("""
        INSERT INTO insiders (name, role, company_id, cik, is_officer, is_director, is_ten_pct)
        VALUES (:name, :role, :company_id, :cik, :is_officer, :is_director, :is_ten_pct)
        ON CONFLICT DO NOTHING
        RETURNING id
    """), {
        "name": reporter["name"],
        "role": reporter.get("role"),
        "company_id": company_id,
        "cik": reporter.get("cik"),
        "is_officer": reporter.get("is_officer", False),
        "is_director": reporter.get("is_director", False),
        "is_ten_pct": reporter.get("is_ten_pct", False),
    }).fetchone()
    return row[0] if row else None


def ingest_filing(db, filing_meta: dict) -> int:
    """Ingest a single Form 4 filing. Returns count of transactions inserted."""
    xml_content = fetch_form4_xml(filing_meta["cik"], filing_meta["accession"])
    if not xml_content:
        return 0

    parsed = parse_form4_xml(xml_content)
    if not parsed or not parsed["transactions"]:
        return 0

    issuer = parsed["issuer"]
    reporter = parsed["reporter"]

    ticker = issuer.get("ticker", "").upper()
    if not ticker:
        return 0

    company_id = upsert_company(db, issuer.get("cik", ""), ticker, issuer.get("name", ""))
    if not company_id:
        return 0

    insider_id = upsert_insider(db, reporter, company_id)
    count = 0

    for tx in parsed["transactions"]:
        try:
            # Compute ownership change %
            ownership_change_pct = None
            ownership_after = tx.get("ownership_after")

            db.execute(text("""
                INSERT INTO insider_transactions
                    (insider_id, company_id, transaction_date, filing_date, transaction_type,
                     shares, price, transaction_value, ownership_after,
                     is_direct, security_title, filing_type, accession_number)
                VALUES
                    (:insider_id, :company_id, :transaction_date, :filing_date, :transaction_type,
                     :shares, :price, :transaction_value, :ownership_after,
                     :is_direct, :security_title, :filing_type, :accession_number)
                ON CONFLICT DO NOTHING
            """), {
                "insider_id": insider_id,
                "company_id": company_id,
                "transaction_date": tx["transaction_date"],
                "filing_date": filing_meta["filing_date"],
                "transaction_type": tx["transaction_type"],
                "shares": tx["shares"],
                "price": tx["price"],
                "transaction_value": tx["transaction_value"],
                "ownership_after": ownership_after,
                "is_direct": tx.get("is_direct", True),
                "security_title": tx.get("security_title"),
                "filing_type": filing_meta["form_type"],
                "accession_number": filing_meta["accession"],
            })
            count += 1
        except Exception as e:
            logger.warning(f"Failed to insert transaction: {e}")

    return count


def run_sec_pipeline(days_back: int = 5):
    """
    Main SEC filing pipeline entry point.
    Fetches recent Form 4s for all tracked companies.
    """
    db = SessionLocal()
    total_ingested = 0

    logger.info("Starting SEC Form 4 pipeline...")

    try:
        # Log pipeline start
        run_id = db.execute(text("""
            INSERT INTO pipeline_runs (pipeline, status)
            VALUES ('sec_filings', 'running')
            RETURNING id
        """)).scalar()
        db.commit()

        # Get all companies with CIK
        companies = db.execute(text(
            "SELECT cik, ticker FROM companies WHERE cik IS NOT NULL ORDER BY market_cap DESC NULLS LAST"
        )).fetchall()

        logger.info(f"Processing {len(companies)} companies")

        for cik, ticker in companies:
            filings = fetch_recent_form4_filings(cik, days_back)
            for filing_meta in filings:
                try:
                    count = ingest_filing(db, filing_meta)
                    total_ingested += count
                    if count > 0:
                        db.commit()
                        logger.info(f"  {ticker}: Ingested {count} transactions from {filing_meta['accession']}")
                except Exception as e:
                    logger.error(f"  {ticker}: Error ingesting {filing_meta['accession']}: {e}")
                    db.rollback()

            time.sleep(0.1)  # SEC rate limit: 10 req/sec

        # Update pipeline run
        db.execute(text("""
            UPDATE pipeline_runs
            SET status='success', ended_at=NOW(), records_processed=:n
            WHERE id=:id
        """), {"n": total_ingested, "id": run_id})
        db.commit()

        logger.info(f"SEC pipeline complete: {total_ingested} transactions ingested")

    except Exception as e:
        logger.error(f"SEC pipeline failed: {e}")
        db.execute(text("""
            UPDATE pipeline_runs
            SET status='failed', ended_at=NOW(), error_message=:err
            WHERE id=:id
        """), {"err": str(e), "id": run_id})
        db.commit()
        raise
    finally:
        db.close()

    return total_ingested
