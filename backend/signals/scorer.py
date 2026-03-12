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
        SELECT AVG(ABS(COALESCE(yoy_growth, 0))) AS avg_growth
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
    # 20%+ YoY growth → score of 10
    business_momentum_score = round(min(10.0, avg_growth / 20.0 * 10), 2)

    # --- Industry Score (0-10): Sector-wide momentum ---
    industry_q = text("""
        SELECT COALESCE(AVG(composite_score), 5) AS sector_avg
        FROM company_composite_scores ccs
        JOIN companies c ON c.id = ccs.company_id
        WHERE c.id = (SELECT sector FROM companies WHERE id = :company_id LIMIT 1)
          AND ccs.date >= :lookback
    """)
    # Simplified: use fixed 5.0 if no cross-sector data yet
    industry_score = 5.0

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


def run_signal_scoring():
    """
    Main entry point: score all unscored transactions
    and recompute composite scores.
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

        scored = 0
        for tx in transactions:
            score_data = score_transaction(
                transaction_id=tx["id"],
                company_id=tx["company_id"],
                insider_id=tx["insider_id"],
                insider_role=tx["insider_role"],
                transaction_date=tx["transaction_date"],
                transaction_type=tx["transaction_type"],
                transaction_value=float(tx["transaction_value"]) if tx["transaction_value"] else None,
                ownership_change_pct=float(tx["ownership_change_pct"]) if tx["ownership_change_pct"] else None,
                db=db,
            )
            if score_data:
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
                        signal_reason = EXCLUDED.signal_reason
                """)
                db.execute(upsert_q, score_data)
                scored += 1

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
