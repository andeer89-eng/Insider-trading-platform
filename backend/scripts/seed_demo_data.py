"""
FINTEL Demo Data Seeder
========================
Generates realistic demo data for all tables to showcase the platform.
Run: python -m scripts.seed_demo_data
"""
import random
import logging
from datetime import date, timedelta
from typing import List
from sqlalchemy import text
from models.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

random.seed(42)

# ---- Realistic insider profiles per company ----
COMPANY_INSIDERS = {
    "TSLA": [
        ("Elon Musk", "CEO", True, False),
        ("Zachary Kirkhorn", "CFO", True, False),
        ("Robyn Denholm", "Chairman", False, True),
        ("James Murdoch", "Director", False, True),
        ("Kathleen Wilson-Thompson", "Director", False, True),
    ],
    "NVDA": [
        ("Jensen Huang", "CEO", True, False),
        ("Colette Kress", "CFO", True, False),
        ("Mark Stevens", "Director", False, True),
        ("Tench Coxe", "Director", False, True),
    ],
    "MSFT": [
        ("Satya Nadella", "CEO", True, False),
        ("Amy Hood", "CFO", True, False),
        ("Brad Smith", "President", True, False),
        ("John Thompson", "Chairman", False, True),
        ("Reid Hoffman", "Director", False, True),
    ],
    "AAPL": [
        ("Tim Cook", "CEO", True, False),
        ("Luca Maestri", "CFO", True, False),
        ("Jeff Williams", "COO", True, False),
        ("Arthur Levinson", "Chairman", False, True),
    ],
    "AMZN": [
        ("Andy Jassy", "CEO", True, False),
        ("Brian Olsavsky", "CFO", True, False),
        ("Jeff Bezos", "Director", False, True),
        ("Judith McGrath", "Director", False, True),
    ],
    "GOOGL": [
        ("Sundar Pichai", "CEO", True, False),
        ("Ruth Porat", "CFO", True, False),
        ("Larry Page", "Director", False, True),
        ("Sergey Brin", "Director", False, True),
        ("John Hennessy", "Chairman", False, True),
    ],
    "META": [
        ("Mark Zuckerberg", "CEO", True, False),
        ("Susan Li", "CFO", True, False),
        ("Sheryl Sandberg", "Director", False, True),
        ("Marc Andreessen", "Director", False, True),
    ],
}

# Default insiders for other companies
DEFAULT_INSIDERS = [
    ("CEO Name", "CEO", True, False),
    ("CFO Name", "CFO", True, False),
    ("Director A", "Director", False, True),
    ("Director B", "Director", False, True),
]


def generate_insider_transactions(
    company_id: int,
    ticker: str,
    insider_ids: List[int],
    insider_roles: List[str],
    days_back: int = 730,
    db=None,
) -> int:
    """Generate realistic insider transaction history."""
    count = 0
    today = date.today()

    # Get approximate share price range based on ticker
    price_ranges = {
        "TSLA": (150, 400), "NVDA": (400, 900), "MSFT": (250, 450),
        "AAPL": (140, 230), "AMZN": (100, 220), "GOOGL": (90, 200),
        "META": (200, 600), "AVGO": (600, 1800), "ORCL": (90, 180),
        "AMD": (80, 210), "CRM": (150, 350), "ADBE": (300, 600),
        "NFLX": (300, 700), "LLY": (500, 900), "JPM": (140, 230),
        "V": (200, 290), "HD": (250, 400), "MA": (350, 510),
    }
    min_price, max_price = price_ranges.get(ticker, (30, 200))

    for insider_id, role in zip(insider_ids, insider_roles):
        # Generate 3-12 trades over the period
        n_trades = random.randint(3, 12)

        for _ in range(n_trades):
            days_ago = random.randint(0, days_back)
            tx_date = today - timedelta(days=days_ago)
            price = round(random.uniform(min_price, max_price), 2)

            # CEOs/CFOs more likely to sell (awards + tax planning)
            is_ceo_cfo = any(r in role.upper() for r in ["CEO", "CFO", "PRESIDENT", "COO"])
            if is_ceo_cfo:
                tx_type = random.choices(["Buy", "Sell", "Award"], weights=[20, 50, 30])[0]
            else:
                tx_type = random.choices(["Buy", "Sell", "Award"], weights=[40, 35, 25])[0]

            # Share amounts based on role
            if "CEO" in role.upper() or "CHAIRMAN" in role.upper():
                if tx_type == "Buy":
                    shares = random.randint(10000, 500000)
                else:
                    shares = random.randint(50000, 2000000)
            elif "CFO" in role.upper() or "COO" in role.upper() or "PRESIDENT" in role.upper():
                shares = random.randint(5000, 200000)
            else:
                shares = random.randint(1000, 50000)

            tx_value = shares * price

            # Ownership simulation
            base_ownership = random.randint(50000, 5000000)
            if tx_type == "Buy":
                ownership_before = base_ownership
                ownership_after = base_ownership + shares
            elif tx_type == "Sell":
                ownership_before = base_ownership + shares
                ownership_after = base_ownership
            else:
                ownership_before = base_ownership
                ownership_after = base_ownership + shares

            ownership_change_pct = (
                (ownership_after - ownership_before) / ownership_before * 100
                if ownership_before > 0 else 0
            )

            db.execute(text("""
                INSERT INTO insider_transactions
                    (insider_id, company_id, transaction_date, filing_date,
                     transaction_type, shares, price, transaction_value,
                     ownership_before, ownership_after, ownership_change_pct,
                     filing_type, is_direct)
                VALUES
                    (:insider_id, :company_id, :tx_date, :filing_date,
                     :tx_type, :shares, :price, :tx_value,
                     :ow_before, :ow_after, :ow_change_pct,
                     'Form4', TRUE)
            """), {
                "insider_id": insider_id,
                "company_id": company_id,
                "tx_date": tx_date,
                "filing_date": tx_date + timedelta(days=random.randint(1, 4)),
                "tx_type": tx_type,
                "shares": shares,
                "price": price,
                "tx_value": tx_value,
                "ow_before": ownership_before,
                "ow_after": ownership_after,
                "ow_change_pct": round(ownership_change_pct, 4),
            })
            count += 1

    return count


def generate_metric_values(company_id: int, ticker: str, db) -> int:
    """Generate time-series metric values for a company."""
    count = 0
    today = date.today()

    # Get metric IDs relevant to this company
    ticker_prefix = ticker.lower()
    metrics = db.execute(text("""
        SELECT id, name, unit FROM metrics
        WHERE name LIKE :prefix OR name IN ('revenue', 'gross_margin', 'free_cash_flow',
              'eps_diluted', 'headcount', 'r_and_d_spend', 'ai_capex_total',
              'datacenter_capacity_mw', 'capex', 'shares_outstanding')
        LIMIT 30
    """), {"prefix": f"{ticker_prefix}_%"}).fetchall()

    # Realistic starting values per metric per company
    metric_seeds = {
        # TSLA
        "tsla_supercharger_sites": (6000, 0.08),
        "tsla_vehicle_deliveries": (400000, 0.25),
        "tsla_vehicle_production": (420000, 0.25),
        "tsla_battery_storage_gwh": (3.5, 0.40),
        "tsla_solar_deployed_mw": (100, 0.15),
        "tsla_automotive_gross_margin": (22, -0.02),
        # NVDA
        "nvda_datacenter_revenue": (10000, 0.90),
        "nvda_gaming_revenue": (2800, -0.05),
        "nvda_gross_margin": (65, 0.05),
        "nvda_cuda_developers": (3.0, 0.30),
        # AMZN
        "amzn_aws_revenue": (23000, 0.17),
        "amzn_prime_subscribers": (200, 0.05),
        "amzn_advertising_revenue": (11000, 0.20),
        "amzn_aws_growth_yoy": (17, 0.0),
        # AAPL
        "aapl_iphone_units": (55, 0.02),
        "aapl_services_revenue": (22000, 0.15),
        "aapl_installed_base": (2.0, 0.08),
        "aapl_services_margin": (74, 0.02),
        # MSFT
        "msft_azure_growth": (28, -0.02),
        "msft_cloud_revenue": (26000, 0.18),
        "msft_office_commercial_seats": (400, 0.12),
        "msft_copilot_seats": (10, 0.50),
        # GOOGL
        "googl_search_revenue": (47000, 0.12),
        "googl_youtube_revenue": (9200, 0.15),
        "googl_cloud_revenue": (10000, 0.28),
        # META
        "meta_dau": (3.1, 0.07),
        "meta_mau": (3.9, 0.05),
        "meta_arpu": (10.5, 0.12),
        "meta_ai_capex": (10, 0.35),
        # Universal
        "revenue": (20000, 0.15),
        "gross_margin": (48, 0.01),
        "free_cash_flow": (5000, 0.20),
        "eps_diluted": (3.5, 0.15),
        "headcount": (50000, 0.05),
        "shares_outstanding": (4000, -0.02),
        "ai_capex_total": (5, 0.40),
        "datacenter_capacity_mw": (500, 0.20),
        "capex": (3000, 0.15),
        "r_and_d_spend": (4000, 0.12),
    }

    company_overrides = {
        "NVDA": {"revenue": (22000, 0.80), "gross_margin": (72, 0.04), "eps_diluted": (5.0, 0.90)},
        "MSFT": {"revenue": (56000, 0.16), "shares_outstanding": (7400, -0.01)},
        "AAPL": {"revenue": (90000, 0.05), "gross_margin": (46, 0.01), "shares_outstanding": (15500, -0.03)},
        "AMZN": {"revenue": (143000, 0.12), "gross_margin": (49, 0.03)},
        "GOOGL": {"revenue": (76000, 0.12), "gross_margin": (56, 0.01)},
        "META": {"revenue": (36000, 0.22), "gross_margin": (80, 0.02)},
        "TSLA": {"revenue": (25000, 0.15), "gross_margin": (17, -0.03)},
    }

    seeds = {**metric_seeds, **company_overrides.get(ticker, {})}

    for metric_id, metric_name, unit in metrics:
        base_val, qoq_growth = seeds.get(metric_name, (random.uniform(10, 1000), random.uniform(-0.05, 0.20)))

        # Generate 20 quarters of history
        current_val = base_val / ((1 + qoq_growth) ** 19)  # work back to start
        quarter_date = today - timedelta(days=19 * 91)

        prev_val = None
        for q in range(20):
            # Add noise
            noise = 1 + random.gauss(0, 0.03)
            quarter_val = max(0, current_val * noise)

            yoy_growth = None
            if q >= 4 and prev_val:
                prev_year_val = current_val / ((1 + qoq_growth) ** 4)
                yoy_growth = (quarter_val - prev_year_val) / prev_year_val * 100 if prev_year_val > 0 else None

            try:
                db.execute(text("""
                    INSERT INTO company_metric_values
                        (company_id, metric_id, date, value, yoy_growth, source, confidence_score)
                    VALUES
                        (:company_id, :metric_id, :date, :value, :yoy_growth, 'demo', 1.0)
                    ON CONFLICT (company_id, metric_id, date) DO NOTHING
                """), {
                    "company_id": company_id,
                    "metric_id": metric_id,
                    "date": quarter_date,
                    "value": round(quarter_val, 4),
                    "yoy_growth": round(yoy_growth, 2) if yoy_growth else None,
                })
                count += 1
            except Exception:
                pass

            prev_val = quarter_val
            current_val = current_val * (1 + qoq_growth)
            quarter_date = quarter_date + timedelta(days=91)

    return count


def generate_composite_scores(company_id: int, db) -> int:
    """Generate composite score history."""
    today = date.today()
    count = 0

    for days_ago in range(0, 365, 30):
        score_date = today - timedelta(days=days_ago)
        insider_score = round(random.uniform(3, 9), 2)
        inst_score = round(random.uniform(4, 8), 2)
        momentum = round(random.uniform(3, 9), 2)
        industry = round(random.uniform(4, 7), 2)
        composite = round(insider_score*0.3 + inst_score*0.25 + momentum*0.25 + industry*0.2, 2)

        try:
            db.execute(text("""
                INSERT INTO company_composite_scores
                    (company_id, date, insider_score, institutional_score,
                     business_momentum_score, industry_score, composite_score, insider_alignment)
                VALUES
                    (:company_id, :date, :ins, :inst, :mom, :ind, :comp, :align)
                ON CONFLICT (company_id, date) DO NOTHING
            """), {
                "company_id": company_id, "date": score_date,
                "ins": insider_score, "inst": inst_score,
                "mom": momentum, "ind": industry, "comp": composite,
                "align": round((insider_score + inst_score) / 2, 2),
            })
            count += 1
        except Exception:
            pass

    return count


def generate_institutional_holdings(company_id: int, ticker: str, db) -> int:
    """Generate institutional holdings for a company."""
    count = 0
    today = date.today()

    # Get all firms
    firms = db.execute(text("SELECT id FROM institutional_firms")).fetchall()

    # Realistic share counts (approximate)
    company_shares = {
        "AAPL": 15_500_000_000, "MSFT": 7_400_000_000, "NVDA": 24_500_000_000,
        "AMZN": 10_400_000_000, "GOOGL": 12_200_000_000, "META": 2_500_000_000,
        "TSLA": 3_200_000_000,
    }
    total_shares = company_shares.get(ticker, random.randint(500_000_000, 5_000_000_000))

    for (firm_id,) in firms:
        # Each firm holds 1-8% of outstanding
        hold_pct = random.uniform(0.01, 0.08)
        base_shares = int(total_shares * hold_pct)

        # Generate 4 quarters of history
        for q in range(4):
            quarter_end = today - timedelta(days=q * 91)
            quarter_end = date(quarter_end.year, ((quarter_end.month - 1) // 3 + 1) * 3, 1)
            # adjust to month end
            import calendar
            last_day = calendar.monthrange(quarter_end.year, quarter_end.month)[1]
            quarter_end = date(quarter_end.year, quarter_end.month, last_day)

            noise = random.gauss(1.0, 0.05)
            shares = max(0, int(base_shares * noise))
            # Estimate value from market cap / shares ratio
            price_est = random.uniform(50, 500)
            value = shares * price_est

            change_shares = random.randint(-int(base_shares * 0.1), int(base_shares * 0.1))
            change_pct = change_shares / base_shares * 100 if base_shares > 0 else 0

            try:
                db.execute(text("""
                    INSERT INTO institutional_holdings
                        (firm_id, company_id, quarter, shares, value,
                         change_shares, change_pct)
                    VALUES
                        (:firm_id, :company_id, :quarter, :shares, :value,
                         :change_shares, :change_pct)
                    ON CONFLICT (firm_id, company_id, quarter) DO NOTHING
                """), {
                    "firm_id": firm_id, "company_id": company_id,
                    "quarter": quarter_end, "shares": shares, "value": int(value),
                    "change_shares": change_shares,
                    "change_pct": round(change_pct, 2),
                })
                count += 1
            except Exception:
                pass

    return count


def generate_cluster_events(company_id: int, ticker: str, insider_ids: list, db) -> int:
    """Generate some cluster buying events."""
    if len(insider_ids) < 2:
        return 0

    today = date.today()
    count = 0

    for _ in range(random.randint(1, 3)):
        days_ago = random.randint(7, 300)
        end_date = today - timedelta(days=days_ago)
        start_date = end_date - timedelta(days=random.randint(5, 14))
        n_insiders = random.randint(2, min(4, len(insider_ids)))
        total_value = random.uniform(500_000, 20_000_000)
        cluster_score = round(random.uniform(6.0, 9.5), 2)

        try:
            db.execute(text("""
                INSERT INTO insider_cluster_events
                    (company_id, start_date, end_date, insider_count,
                     total_value, cluster_score)
                VALUES
                    (:company_id, :start, :end, :n, :value, :score)
            """), {
                "company_id": company_id, "start": start_date, "end": end_date,
                "n": n_insiders, "value": total_value, "score": cluster_score,
            })
            count += 1
        except Exception:
            pass

    return count


def run_seeder():
    """Main seeder entry point."""
    db = SessionLocal()

    logger.info("=" * 60)
    logger.info("FINTEL Demo Data Seeder")
    logger.info("=" * 60)

    try:
        # Get all companies
        companies = db.execute(text(
            "SELECT id, ticker, name FROM companies ORDER BY market_cap DESC NULLS LAST"
        )).fetchall()

        logger.info(f"Seeding data for {len(companies)} companies...")

        for company_id, ticker, name in companies:
            logger.info(f"  [{ticker}] {name}")

            # Create insiders
            insider_data = COMPANY_INSIDERS.get(ticker, DEFAULT_INSIDERS)
            insider_ids = []
            insider_roles = []

            for ins_name, role, is_officer, is_director in insider_data:
                display_name = ins_name if ticker in COMPANY_INSIDERS else f"{ticker} {ins_name}"
                row = db.execute(text("""
                    INSERT INTO insiders (name, role, company_id, is_officer, is_director)
                    VALUES (:name, :role, :company_id, :is_officer, :is_director)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """), {
                    "name": display_name, "role": role, "company_id": company_id,
                    "is_officer": is_officer, "is_director": is_director,
                }).fetchone()

                if row:
                    insider_ids.append(row[0])
                    insider_roles.append(role)

            if not insider_ids:
                insider_rows = db.execute(text(
                    "SELECT id, role FROM insiders WHERE company_id = :cid"
                ), {"cid": company_id}).fetchall()
                insider_ids = [r[0] for r in insider_rows]
                insider_roles = [r[1] for r in insider_rows]

            db.commit()

            # Generate transactions
            n_tx = generate_insider_transactions(
                company_id, ticker, insider_ids, insider_roles, days_back=730, db=db
            )
            db.commit()
            logger.info(f"    → {n_tx} transactions")

            # Generate metrics
            n_metrics = generate_metric_values(company_id, ticker, db)
            db.commit()
            logger.info(f"    → {n_metrics} metric data points")

            # Generate institutional holdings
            n_inst = generate_institutional_holdings(company_id, ticker, db)
            db.commit()
            logger.info(f"    → {n_inst} institutional holdings")

            # Generate composite scores
            n_scores = generate_composite_scores(company_id, db)
            db.commit()
            logger.info(f"    → {n_scores} composite score entries")

            # Generate cluster events
            n_clusters = generate_cluster_events(company_id, ticker, insider_ids, db)
            db.commit()
            logger.info(f"    → {n_clusters} cluster events")

        # Run signal scoring on all generated transactions
        logger.info("\nRunning signal scoring on generated transactions...")
        from signals.scorer import run_signal_scoring
        run_signal_scoring()

        logger.info("\n" + "=" * 60)
        logger.info("Demo data seeding complete!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Seeder failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seeder()
