"""
FINTEL Signal Scoring Engine
============================
Scores each insider transaction on a 0-10 scale using:
  1. Trade size (relative to compensation/ownership)
  2. Insider role (CEO > CFO > Director)
  3. Insider historical alpha (skill score)
  4. Ownership change %
  5. Cluster detection (multiple insiders buying same company)
"""
import logging
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.database import SessionLocal
from lib.cache import invalidate_prefix

logger = logging.getLogger(__name__)

# Role scoring weights
ROLE_WEIGHTS = {
    "CEO": 10.0,
    "Chief Executive Officer": 10.0,
    "CFO": 8.5,
    "Chief Financial Officer": 8.5,
    "COO": 8.0,
    "Chief Operating Officer": 8.0,
    "CTO": 7.5,
    "Chief Technology Officer": 7.5,
    "President": 9.0,
    "Director": 6.0,
    "Chairman": 9.5,
    "EVP": 7.0,
    "Executive Vice President": 7.0,
    "SVP": 6.5,
    "Senior Vice President": 6.5,
    "VP": 5.5,
    "Vice President": 5.5,
    "General Counsel": 6.0,
    "10% Owner": 7.0,
}

# Value thresholds for size scoring
VALUE_TIERS = [
    (10_000_000, 10.0),   # $10M+  → max score
    (5_000_000,   9.0),   # $5M-10M
    (2_000_000,   8.0),   # $2M-5M
    (1_000_000,   7.0),   # $1M-2M
    (500_000,     6.0),   # $500K-1M
    (250_000,     5.0),   # $250K-500K
    (100_000,     4.0),   # $100K-250K
    (50_000,      3.0),   # $50K-100K
    (0,           1.0),   # <$50K
]

CLUSTER_WINDOW_DAYS = 14
CLUSTER_MIN_INSIDERS = 2


def get_role_score(role: Optional[str]) -> float:
    """Score an insider's role (0-10)."""
    if not role:
        return 5.0
    for key, score in ROLE_WEIGHTS.items():
        if key.lower() in role.lower():
            return score
    return 5.0


def get_size_score(transaction_value: Optional[float]) -> float:
    """Score trade size (0-10)."""
    if not transaction_value or transaction_value <= 0:
        return 1.0
    for threshold, score in VALUE_TIERS:
        if transaction_value >= threshold:
            return score
    return 1.0


def get_ownership_score(ownership_change_pct: Optional[float]) -> float:
    """Score ownership change (0-10). Larger ownership increases → higher score."""
    if not ownership_change_pct or ownership_change_pct <= 0:
        return 0.0
    if ownership_change_pct >= 50:
        return 10.0
    elif ownership_change_pct >= 25:
        return 9.0
    elif ownership_change_pct >= 10:
        return 8.0
    elif ownership_change_pct >= 5:
        return 7.0
    elif ownership_change_pct >= 2:
        return 5.0
    elif ownership_change_pct >= 1:
        return 3.0
    return 1.0


def get_insider_skill_score(insider_id: int, db: Session) -> float:
    """
    Compute historical skill score for an insider.
    Based on: win rate on 30d returns from past buys.
    """
    q = text("""
        SELECT
            COUNT(*) AS n_buys,
            COUNT(CASE WHEN ito.return_30d > 0 THEN 1 END) AS n_wins,
            AVG(ito.alpha_30d) AS avg_alpha
        FROM insider_transactions it
        JOIN insider_trade_outcomes ito ON ito.transaction_id = it.id
        WHERE it.insider_id = :insider_id
          AND it.transaction_type IN ('Buy', 'Purchase')
          AND ito.return_30d IS NOT NULL
    """)
    row = db.execute(q, {"insider_id": insider_id}).mappings().first()

    if not row or not row["n_buys"] or row["n_buys"] < 2:
        return 5.0  # neutral if no history

    n_buys = row["n_buys"]
    n_wins = row["n_wins"] or 0
    avg_alpha = float(row["avg_alpha"] or 0)

    win_rate = n_wins / n_buys
    # Skill score: 60% win rate + 40% average alpha
    # Alpha normalized: assume ±0.10 (10%) range maps to ±5 points
    alpha_score = min(10.0, max(0.0, 5.0 + avg_alpha * 50))
    skill_score = (win_rate * 10 * 0.6) + (alpha_score * 0.4)
    return round(min(10.0, max(0.0, skill_score)), 2)


def detect_cluster(company_id: int, transaction_date: date, db: Session) -> bool:
    """
    Check if this trade is part of a cluster (multiple insiders buying within 14 days).
    """
    window_start = transaction_date - timedelta(days=CLUSTER_WINDOW_DAYS)
    q = text("""
        SELECT COUNT(DISTINCT insider_id) AS n_insiders
        FROM insider_transactions
        WHERE company_id = :company_id
          AND transaction_type IN ('Buy', 'Purchase')
          AND transaction_date BETWEEN :start AND :end
          AND insider_id IS NOT NULL
    """)
    row = db.execute(q, {
        "company_id": company_id,
        "start": window_start,
        "end": transaction_date,
    }).fetchone()
    return (row[0] or 0) >= CLUSTER_MIN_INSIDERS


def score_transaction(
    transaction_id: int,
    company_id: int,
    insider_id: Optional[int],
    insider_role: Optional[str],
    transaction_date: date,
    transaction_type: str,
    transaction_value: Optional[float],
    ownership_change_pct: Optional[float],
    db: Session,
) -> dict:
    """
    Score a single insider transaction.
    Returns a dict matching the insider_signal_scores table.
    """
    if transaction_type not in ("Buy", "Purchase"):
        return {}  # Only score purchases

    # Component scores
    role_score = get_role_score(insider_role)
    size_score = get_size_score(transaction_value)
    ownership_score = get_ownership_score(ownership_change_pct)
    history_score = get_insider_skill_score(insider_id, db) if insider_id else 5.0
    cluster_flag = detect_cluster(company_id, transaction_date, db)

    # Weighted composite score (0-10)
    # Weights: role=25%, size=30%, ownership=20%, history=15%, cluster bonus=10%
    base_score = (
        role_score * 0.25 +
        size_score * 0.30 +
        ownership_score * 0.20 +
        history_score * 0.15
    )

    cluster_bonus = 1.0 if cluster_flag else 0.0
    final_score = min(10.0, base_score + cluster_bonus)

    # Build reason string
    reasons = []
    if role_score >= 9:
        reasons.append(f"C-suite executive ({insider_role})")
    if size_score >= 8:
        reasons.append(f"Large purchase (${transaction_value:,.0f})" if transaction_value else "Large purchase")
    if ownership_score >= 7:
        reasons.append(f"+{ownership_change_pct:.1f}% ownership increase")
    if cluster_flag:
        reasons.append("Cluster buying detected")
    if history_score >= 7:
        reasons.append("High-performing insider (historical alpha)")

    signal_reason = "; ".join(reasons) if reasons else "Standard insider purchase"

    return {
        "transaction_id": transaction_id,
        "score": round(final_score, 2),
        "size_score": round(size_score, 2),
        "role_score": round(role_score, 2),
        "history_score": round(history_score, 2),
        "ownership_score": round(ownership_score, 2),
        "cluster_flag": cluster_flag,
        "ownership_change_pct": ownership_change_pct,
        "insider_skill_score": round(history_score, 2),
        "signal_reason": signal_reason,
    }


def compute_composite_score(company_id: int, score_date: date, db: Session) -> dict:
    """
    Compute the composite opportunity score for a company on a given date.

    Composite = 30% insider + 25% institutional + 25% business_momentum + 20% industry
    """
    # --- Insider Score (0-10): Recent buy conviction ---
    insider_q = text("""
        SELECT
            COALESCE(AVG(iss.score), 5) AS avg_signal_score,
            COUNT(CASE WHEN it.transaction_type IN ('Buy','Purchase')
                       AND it.transaction_date >= :lookback THEN 1 END) AS buy_count,
            COUNT(CASE WHEN it.transaction_type IN ('Sell','Sale')
                       AND it.transaction_date >= :lookback THEN 1 END) AS sell_count
        FROM insider_transactions it
        LEFT JOIN insider_signal_scores iss ON iss.transaction_id = it.id
        WHERE it.company_id = :company_id
          AND it.transaction_date >= :lookback
    """)
    ins = db.execute(insider_q, {
        "company_id": company_id,
        "lookback": score_date - timedelta(days=90),
    }).mappings().first()

    buy_count = ins["buy_count"] or 0
    sell_count = ins["sell_count"] or 0
    total_trades = buy_count + sell_count
    buy_ratio = buy_count / total_trades if total_trades > 0 else 0.5
    insider_score = float(ins["avg_signal_score"]) * buy_ratio
    insider_score = round(min(10.0, insider_score), 2)

    # --- Institutional Score (0-10): Accumulation vs distribution ---
    inst_q = text("""
        SELECT
            COUNT(CASE WHEN change_shares > 0 THEN 1 END) AS buyers,
            COUNT(CASE WHEN change_shares < 0 THEN 1 END) AS sellers,
            COUNT(*) AS total
        FROM institutional_holdings
        WHERE company_id = :company_id
          AND quarter >= :lookback
    """)
    inst = db.execute(inst_q, {
        "company_id": company_id,
        "lookback": score_date - timedelta(days=120),
    }).mappings().first()

    inst_total = inst["total"] or 0
    inst_buyers = inst["buyers"] or 0
    institutional_score = round((inst_buyers / inst_total * 10) if inst_total > 0 else 5.0, 2)

    # --- Business Momentum Score (0-10): YoY metric growth ---
    momentum_q = text("""
        SELECT AVG(COALESCE(yoy_growth, 0)) AS avg_growth
        FROM company_metric_values cmv
        JOIN metrics m ON m.id = cmv.metric_id
        WHERE cmv.company_id = :company_id
          AND m.category IN ('financial', 'production', 'product')
          AND cmv.date >= :lookback
          AND yoy_growth IS NOT NULL
    """)
    mom = db.execute(momentum_q, {
        "company_id": company_id,
        "lookback": score_date - timedelta(days=365),
    }).mappings().first()

    avg_growth = float(mom["avg_growth"] or 0)
    # Maps: -20% → 0, 0% → 5, +20% → 10 (linear, clamped)
    business_momentum_score = round(min(10.0, max(0.0, 5.0 + avg_growth / 20.0 * 5)), 2)

    # --- Industry Score (0-10): Sector-wide momentum ---
    industry_q = text("""
        SELECT COALESCE(AVG(ccs2.composite_score), 5) AS sector_avg
        FROM company_composite_scores ccs2
        JOIN companies c2 ON c2.id = ccs2.company_id
        WHERE c2.sector = (SELECT sector FROM companies WHERE id = :company_id)
          AND c2.id != :company_id
          AND ccs2.date >= :industry_lookback
    """)
    ind = db.execute(industry_q, {
        "company_id": company_id,
        "industry_lookback": score_date - timedelta(days=90),
    }).mappings().first()
    industry_score = round(float(ind["sector_avg"]) if ind and ind["sector_avg"] else 5.0, 2)

    # --- Composite ---
    composite = round(
        insider_score * 0.30 +
        institutional_score * 0.25 +
        business_momentum_score * 0.25 +
        industry_score * 0.20,
        2
    )

    insider_alignment = round(
        (insider_score + institutional_score) / 2, 2
    )

    return {
        "company_id": company_id,
        "date": score_date,
        "insider_score": insider_score,
        "institutional_score": institutional_score,
        "business_momentum_score": business_momentum_score,
        "industry_score": industry_score,
        "composite_score": composite,
        "insider_alignment": insider_alignment,
    }


def _bulk_fetch_skill_scores(insider_ids: list, db: Session) -> dict:
    """
    Fetch historical win-rate and alpha for a batch of insiders in one query.
    Returns {insider_id: {"n_buys": int, "n_wins": int, "avg_alpha": float}}.
    """
    if not insider_ids:
        return {}
    rows = db.execute(text("""
        SELECT
            it.insider_id,
            COUNT(*) AS n_buys,
            COUNT(CASE WHEN ito.return_30d > 0 THEN 1 END) AS n_wins,
            AVG(ito.alpha_30d) AS avg_alpha
        FROM insider_transactions it
        JOIN insider_trade_outcomes ito ON ito.transaction_id = it.id
        WHERE it.insider_id = ANY(:ids)
          AND it.transaction_type IN ('Buy', 'Purchase')
          AND ito.return_30d IS NOT NULL
        GROUP BY it.insider_id
    """), {"ids": list(insider_ids)}).mappings().all()
    return {r["insider_id"]: r for r in rows}


def _bulk_fetch_clusters(company_ids: list, window_days: int, db: Session) -> set:
    """
    Return the set of company_ids where >= CLUSTER_MIN_INSIDERS distinct insiders
    have bought within the last `window_days` days.
    """
    if not company_ids:
        return set()
    rows = db.execute(text("""
        SELECT company_id
        FROM insider_transactions
        WHERE company_id = ANY(:ids)
          AND transaction_type IN ('Buy', 'Purchase')
          AND transaction_date >= CURRENT_DATE - INTERVAL '14 days'
          AND insider_id IS NOT NULL
        GROUP BY company_id
        HAVING COUNT(DISTINCT insider_id) >= :min_insiders
    """), {"ids": list(company_ids), "min_insiders": CLUSTER_MIN_INSIDERS}).fetchall()
    return {r[0] for r in rows}


def _compute_skill_score_from_row(row) -> float:
    """Compute skill score from a pre-fetched aggregate row (no DB call)."""
    if not row or not row["n_buys"] or row["n_buys"] < 2:
        return 5.0
    n_buys = row["n_buys"]
    n_wins = row["n_wins"] or 0
    avg_alpha = float(row["avg_alpha"] or 0)
    win_rate = n_wins / n_buys
    alpha_score = min(10.0, max(0.0, 5.0 + avg_alpha * 50))
    return round(min(10.0, max(0.0, (win_rate * 10 * 0.6) + (alpha_score * 0.4))), 2)


def run_signal_scoring():
    """
    Main entry point: score all unscored transactions
    and recompute composite scores.

    Uses bulk DB queries to avoid N+1 round-trips:
      - insider skill scores: 1 query for all insiders
      - cluster detection: 1 query for all companies
      - score upserts: batched executemany
    """
    db = SessionLocal()
    logger.info("Starting signal scoring run...")

    try:
        # Get unscored buy transactions
        unscored_q = text("""
            SELECT
                it.id, it.company_id, it.insider_id,
                it.transaction_date, it.transaction_type,
                it.transaction_value, it.ownership_change_pct,
                i.role AS insider_role
            FROM insider_transactions it
            LEFT JOIN insiders i ON i.id = it.insider_id
            LEFT JOIN insider_signal_scores iss ON iss.transaction_id = it.id
            WHERE it.transaction_type IN ('Buy', 'Purchase')
              AND iss.transaction_id IS NULL
            ORDER BY it.transaction_date DESC
            LIMIT 1000
        """)
        transactions = db.execute(unscored_q).mappings().all()
        logger.info(f"Scoring {len(transactions)} unscored transactions")

        if not transactions:
            logger.info("No unscored transactions found.")
        else:
            # Bulk-fetch all needed data in 2 queries instead of 2×N queries
            insider_ids = {tx["insider_id"] for tx in transactions if tx["insider_id"]}
            company_ids = {tx["company_id"] for tx in transactions}

            skill_map = _bulk_fetch_skill_scores(insider_ids, db)
            cluster_companies = _bulk_fetch_clusters(company_ids, CLUSTER_WINDOW_DAYS, db)

            # Score in-memory
            scored = 0
            score_rows = []
            for tx in transactions:
                if tx["transaction_type"] not in ("Buy", "Purchase"):
                    continue

                role_score = get_role_score(tx["insider_role"])
                size_score = get_size_score(
                    float(tx["transaction_value"]) if tx["transaction_value"] else None
                )
                ownership_score = get_ownership_score(
                    float(tx["ownership_change_pct"]) if tx["ownership_change_pct"] else None
                )
                history_score = _compute_skill_score_from_row(
                    skill_map.get(tx["insider_id"])
                ) if tx["insider_id"] else 5.0
                cluster_flag = tx["company_id"] in cluster_companies

                base_score = (
                    role_score * 0.25 +
                    size_score * 0.30 +
                    ownership_score * 0.20 +
                    history_score * 0.15
                )
                final_score = min(10.0, base_score + (1.0 if cluster_flag else 0.0))

                reasons = []
                if role_score >= 9:
                    reasons.append(f"C-suite executive ({tx['insider_role']})")
                if size_score >= 8:
                    val = tx["transaction_value"]
                    reasons.append(f"Large purchase (${float(val):,.0f})" if val else "Large purchase")
                if ownership_score >= 7:
                    pct = tx["ownership_change_pct"]
                    reasons.append(f"+{float(pct):.1f}% ownership increase" if pct else "Ownership increase")
                if cluster_flag:
                    reasons.append("Cluster buying detected")
                if history_score >= 7:
                    reasons.append("High-performing insider (historical alpha)")

                score_rows.append({
                    "transaction_id": tx["id"],
                    "score": round(final_score, 2),
                    "size_score": round(size_score, 2),
                    "role_score": round(role_score, 2),
                    "history_score": round(history_score, 2),
                    "ownership_score": round(ownership_score, 2),
                    "cluster_flag": cluster_flag,
                    "ownership_change_pct": float(tx["ownership_change_pct"]) if tx["ownership_change_pct"] else None,
                    "insider_skill_score": round(history_score, 2),
                    "signal_reason": "; ".join(reasons) if reasons else "Standard insider purchase",
                })
                scored += 1

            # Bulk upsert all scored rows
            if score_rows:
                upsert_q = text("""
                    INSERT INTO insider_signal_scores
                        (transaction_id, score, size_score, role_score, history_score,
                         ownership_score, cluster_flag, ownership_change_pct,
                         insider_skill_score, signal_reason)
                    VALUES
                        (:transaction_id, :score, :size_score, :role_score, :history_score,
                         :ownership_score, :cluster_flag, :ownership_change_pct,
                         :insider_skill_score, :signal_reason)
                    ON CONFLICT (transaction_id) DO UPDATE SET
                        score = EXCLUDED.score,
                        cluster_flag = EXCLUDED.cluster_flag,
                        signal_reason = EXCLUDED.signal_reason,
                        updated_at = NOW()
                """)
                db.execute(upsert_q, score_rows)

        db.commit()
        logger.info(f"Scored {scored} transactions")

        # Recompute composite scores for all companies with recent activity
        companies_q = text("""
            SELECT DISTINCT company_id FROM insider_transactions
            WHERE transaction_date >= CURRENT_DATE - INTERVAL '90 days'
        """)
        companies = db.execute(companies_q).fetchall()
        today = date.today()

        for (company_id,) in companies:
            score_data = compute_composite_score(company_id, today, db)
            upsert_q = text("""
                INSERT INTO company_composite_scores
                    (company_id, date, insider_score, institutional_score,
                     business_momentum_score, industry_score, composite_score, insider_alignment)
                VALUES
                    (:company_id, :date, :insider_score, :institutional_score,
                     :business_momentum_score, :industry_score, :composite_score, :insider_alignment)
                ON CONFLICT (company_id, date) DO UPDATE SET
                    insider_score = EXCLUDED.insider_score,
                    composite_score = EXCLUDED.composite_score,
                    insider_alignment = EXCLUDED.insider_alignment
            """)
            db.execute(upsert_q, score_data)

        db.commit()
        logger.info(f"Recomputed composite scores for {len(companies)} companies")

        # Invalidate all cached leaderboard / dashboard / composite-score keys
        # so the next API request reflects freshly computed scores immediately.
        for prefix in ("leaderboard:", "dashboard", "composite_scores:"):
            n_evicted = invalidate_prefix(prefix)
            if n_evicted:
                logger.info(f"Evicted {n_evicted} cache keys for prefix '{prefix}'")

        # Log pipeline run
        db.execute(text("""
            INSERT INTO pipeline_runs (pipeline, status, ended_at, records_processed)
            VALUES ('signal_scoring', 'success', NOW(), :n)
        """), {"n": scored})
        db.commit()

    except Exception as e:
        logger.error(f"Signal scoring failed: {e}")
        db.execute(text("""
            INSERT INTO pipeline_runs (pipeline, status, ended_at, error_message)
            VALUES ('signal_scoring', 'failed', NOW(), :err)
        """), {"err": str(e)})
        db.commit()
        raise
    finally:
        db.close()
