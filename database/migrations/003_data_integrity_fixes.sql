-- ============================================================
-- Migration 003: Data Integrity Fixes
-- ============================================================
-- Adds:
--   1. UNIQUE constraint on insider_transactions to prevent duplicate
--      ingestion on re-runs of the SEC pipeline.
--   2. Covering index on (company_id, transaction_type, transaction_date)
--      to accelerate the leaderboard buys_30d aggregation.
--   3. Index on insider_signal_scores (transaction_id) for fast JOIN
--      lookups during signal scoring.
--   4. updated_at column on insider_signal_scores so rescoring is auditable.
-- ============================================================

BEGIN;

-- 1. Unique constraint: one row per (company, accession filing, date, type, shares).
--    accession_number uniquely identifies a Form 4 filing; combined with the
--    transaction fields it uniquely identifies each reported trade line.
ALTER TABLE insider_transactions
    ADD CONSTRAINT uq_insider_transaction
    UNIQUE (company_id, accession_number, transaction_date, transaction_type, shares);

-- 2. Composite index for buy-count aggregations used by the leaderboard and cluster detection.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_txn_company_type_date
    ON insider_transactions (company_id, transaction_type, transaction_date DESC);

-- 3. Index for the insider skill-score JOIN (scorer.py get_insider_skill_score).
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_txn_insider_type
    ON insider_transactions (insider_id, transaction_type);

-- 4. Track when a signal score was last (re)calculated.
ALTER TABLE insider_signal_scores
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Backfill updated_at for existing rows.
UPDATE insider_signal_scores SET updated_at = created_at WHERE updated_at IS NULL;

-- Trigger to auto-update updated_at on upsert.
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_signal_scores_updated_at ON insider_signal_scores;
CREATE TRIGGER trg_signal_scores_updated_at
    BEFORE UPDATE ON insider_signal_scores
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
