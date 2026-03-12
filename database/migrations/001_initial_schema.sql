-- ============================================================
-- FINTEL: Financial Intelligence Platform
-- Migration 001: Initial Schema
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- COMPANIES
-- ============================================================
CREATE TABLE companies (
    id          SERIAL PRIMARY KEY,
    ticker      VARCHAR(10) UNIQUE NOT NULL,
    name        VARCHAR(255) NOT NULL,
    sector      VARCHAR(100),
    industry    VARCHAR(100),
    country     VARCHAR(50) DEFAULT 'US',
    market_cap  BIGINT,
    ipo_date    DATE,
    cik         VARCHAR(20) UNIQUE,          -- SEC CIK number
    exchange    VARCHAR(20),                  -- NYSE, NASDAQ
    description TEXT,
    website     VARCHAR(255),
    logo_url    VARCHAR(500),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_companies_ticker ON companies(ticker);
CREATE INDEX idx_companies_sector ON companies(sector);
CREATE INDEX idx_companies_industry ON companies(industry);
CREATE INDEX idx_companies_name_trgm ON companies USING gin(name gin_trgm_ops);

-- ============================================================
-- INSIDERS
-- ============================================================
CREATE TABLE insiders (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    role            VARCHAR(100),               -- CEO, CFO, Director, etc.
    company_id      INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    cik             VARCHAR(20),                 -- Individual CIK
    first_seen_date DATE,
    is_officer      BOOLEAN DEFAULT FALSE,
    is_director     BOOLEAN DEFAULT FALSE,
    is_ten_pct      BOOLEAN DEFAULT FALSE,       -- 10% beneficial owner
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_insiders_company ON insiders(company_id);
CREATE INDEX idx_insiders_name ON insiders(name);

-- ============================================================
-- INSIDER TRANSACTIONS
-- ============================================================
CREATE TABLE insider_transactions (
    id                  SERIAL PRIMARY KEY,
    insider_id          INTEGER REFERENCES insiders(id) ON DELETE SET NULL,
    company_id          INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    transaction_date    DATE NOT NULL,
    filing_date         DATE,
    transaction_type    VARCHAR(20) NOT NULL,    -- Buy, Sell, Award, Exercise, etc.
    shares              NUMERIC(18, 4) NOT NULL,
    price               NUMERIC(18, 4),
    transaction_value   NUMERIC(18, 2),          -- shares * price
    ownership_before    NUMERIC(18, 4),
    ownership_after     NUMERIC(18, 4),
    ownership_change_pct NUMERIC(8, 4),
    filing_type         VARCHAR(10),             -- Form3, Form4, Form5
    filing_url          VARCHAR(500),
    accession_number    VARCHAR(50),
    form_type           VARCHAR(10),
    security_title      VARCHAR(100),
    is_direct           BOOLEAN DEFAULT TRUE,
    footnote            TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transactions_company ON insider_transactions(company_id);
CREATE INDEX idx_transactions_insider ON insider_transactions(insider_id);
CREATE INDEX idx_transactions_date ON insider_transactions(transaction_date DESC);
CREATE INDEX idx_transactions_type ON insider_transactions(transaction_type);

-- ============================================================
-- INSIDER TRADE OUTCOMES (forward returns)
-- ============================================================
CREATE TABLE insider_trade_outcomes (
    id              SERIAL PRIMARY KEY,
    transaction_id  INTEGER UNIQUE REFERENCES insider_transactions(id) ON DELETE CASCADE,
    return_7d       NUMERIC(10, 6),
    return_30d      NUMERIC(10, 6),
    return_90d      NUMERIC(10, 6),
    return_1y       NUMERIC(10, 6),
    return_2y       NUMERIC(10, 6),
    benchmark_return_7d  NUMERIC(10, 6),        -- S&P 500 return same period
    benchmark_return_30d NUMERIC(10, 6),
    benchmark_return_90d NUMERIC(10, 6),
    benchmark_return_1y  NUMERIC(10, 6),
    alpha_7d        NUMERIC(10, 6),             -- return - benchmark
    alpha_30d       NUMERIC(10, 6),
    alpha_90d       NUMERIC(10, 6),
    alpha_1y        NUMERIC(10, 6),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INSTITUTIONAL FIRMS
-- ============================================================
CREATE TABLE institutional_firms (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    cik         VARCHAR(20) UNIQUE,
    type        VARCHAR(50),                    -- HedgeFund, Mutual, Pension, etc.
    aum         BIGINT,                         -- Assets under management
    country     VARCHAR(50),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_firms_name ON institutional_firms(name);

-- ============================================================
-- INSTITUTIONAL HOLDINGS (from 13F filings)
-- ============================================================
CREATE TABLE institutional_holdings (
    id              SERIAL PRIMARY KEY,
    firm_id         INTEGER NOT NULL REFERENCES institutional_firms(id) ON DELETE CASCADE,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    quarter         DATE NOT NULL,              -- e.g. 2024-12-31 (quarter end)
    shares          BIGINT,
    value           BIGINT,                     -- USD value
    shares_prev     BIGINT,                     -- previous quarter
    value_prev      BIGINT,
    change_shares   BIGINT,                     -- delta
    change_pct      NUMERIC(10, 4),
    filing_date     DATE,
    accession_number VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (firm_id, company_id, quarter)
);

CREATE INDEX idx_holdings_company ON institutional_holdings(company_id, quarter DESC);
CREATE INDEX idx_holdings_firm ON institutional_holdings(firm_id, quarter DESC);

-- ============================================================
-- METRIC REGISTRY
-- ============================================================
CREATE TABLE metrics (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) UNIQUE NOT NULL,   -- e.g. supercharger_sites
    display_name VARCHAR(200),
    category    VARCHAR(50) NOT NULL,           -- infrastructure, production, financial, etc.
    subcategory VARCHAR(50),
    unit        VARCHAR(50),                    -- count, GWh, MW, $M, etc.
    description TEXT,
    source      VARCHAR(100),                   -- earnings, 10K, third_party
    frequency   VARCHAR(20),                    -- quarterly, annual, monthly
    is_public   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metrics_category ON metrics(category);
CREATE INDEX idx_metrics_name ON metrics(name);

-- ============================================================
-- COMPANY METRIC VALUES (time-series star schema fact table)
-- ============================================================
CREATE TABLE company_metric_values (
    id              BIGSERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    metric_id       INTEGER NOT NULL REFERENCES metrics(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    value           NUMERIC(20, 6),
    value_prev      NUMERIC(20, 6),             -- prior period value
    yoy_growth      NUMERIC(10, 4),             -- year-over-year growth %
    source          VARCHAR(100),
    confidence_score NUMERIC(5, 2) DEFAULT 1.0, -- 0-1 confidence
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (company_id, metric_id, date)
);

CREATE INDEX idx_metric_values_company ON company_metric_values(company_id, metric_id, date DESC);
CREATE INDEX idx_metric_values_metric ON company_metric_values(metric_id, date DESC);
CREATE INDEX idx_metric_values_date ON company_metric_values(date DESC);

-- ============================================================
-- SIGNAL TABLES
-- ============================================================

-- Insider cluster events
CREATE TABLE insider_cluster_events (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    insider_count   INTEGER NOT NULL,
    total_shares    NUMERIC(18, 4),
    total_value     NUMERIC(18, 2),
    unique_roles    TEXT[],                     -- array of roles involved
    cluster_score   NUMERIC(5, 2),              -- 0-10
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_clusters_company ON insider_cluster_events(company_id, end_date DESC);

-- Insider signal scores (per transaction)
CREATE TABLE insider_signal_scores (
    id                  SERIAL PRIMARY KEY,
    transaction_id      INTEGER UNIQUE REFERENCES insider_transactions(id) ON DELETE CASCADE,
    score               NUMERIC(5, 2),          -- 0-10 total signal score
    size_score          NUMERIC(5, 2),          -- large relative to compensation
    role_score          NUMERIC(5, 2),          -- CEO > CFO > Director
    history_score       NUMERIC(5, 2),          -- insider's historical alpha
    ownership_score     NUMERIC(5, 2),          -- ownership change %
    cluster_flag        BOOLEAN DEFAULT FALSE,
    ownership_change_pct NUMERIC(10, 4),
    insider_skill_score  NUMERIC(5, 2),         -- historical win rate
    signal_reason       TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Company composite scores
CREATE TABLE company_composite_scores (
    id                      BIGSERIAL PRIMARY KEY,
    company_id              INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    date                    DATE NOT NULL,
    insider_score           NUMERIC(5, 2),      -- 0-10
    institutional_score     NUMERIC(5, 2),
    business_momentum_score NUMERIC(5, 2),
    industry_score          NUMERIC(5, 2),
    composite_score         NUMERIC(5, 2),      -- weighted average
    insider_alignment       NUMERIC(5, 2),      -- insiders + institutions aligned
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (company_id, date)
);

CREATE INDEX idx_composite_scores_company ON company_composite_scores(company_id, date DESC);
CREATE INDEX idx_composite_scores_date ON company_composite_scores(date DESC, composite_score DESC);

-- ============================================================
-- STOCK PRICES (for return calculations)
-- ============================================================
CREATE TABLE stock_prices (
    id          BIGSERIAL PRIMARY KEY,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    date        DATE NOT NULL,
    open        NUMERIC(12, 4),
    high        NUMERIC(12, 4),
    low         NUMERIC(12, 4),
    close       NUMERIC(12, 4) NOT NULL,
    adj_close   NUMERIC(12, 4),
    volume      BIGINT,
    UNIQUE (company_id, date)
);

CREATE INDEX idx_prices_company ON stock_prices(company_id, date DESC);

-- ============================================================
-- EARNINGS TRANSCRIPTS
-- ============================================================
CREATE TABLE earnings_transcripts (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    fiscal_quarter  VARCHAR(10),                -- Q1 2024
    fiscal_year     INTEGER,
    call_date       DATE,
    transcript_url  VARCHAR(500),
    raw_text        TEXT,
    processed       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transcripts_company ON earnings_transcripts(company_id, call_date DESC);

-- ============================================================
-- DATA PIPELINE RUNS (audit log)
-- ============================================================
CREATE TABLE pipeline_runs (
    id          SERIAL PRIMARY KEY,
    pipeline    VARCHAR(100) NOT NULL,
    status      VARCHAR(20) NOT NULL,           -- running, success, failed
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    ended_at    TIMESTAMPTZ,
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    metadata    JSONB
);

CREATE INDEX idx_pipeline_runs ON pipeline_runs(pipeline, started_at DESC);

-- ============================================================
-- USEFUL VIEWS
-- ============================================================

-- Latest company scores
CREATE VIEW latest_company_scores AS
SELECT DISTINCT ON (company_id)
    ccs.*,
    c.ticker,
    c.name,
    c.sector,
    c.industry,
    c.market_cap
FROM company_composite_scores ccs
JOIN companies c ON c.id = ccs.company_id
ORDER BY company_id, date DESC;

-- Recent insider transactions with metadata
CREATE VIEW recent_insider_trades AS
SELECT
    it.*,
    i.name AS insider_name,
    i.role AS insider_role,
    c.ticker,
    c.name AS company_name,
    c.sector,
    iss.score AS signal_score,
    iss.cluster_flag
FROM insider_transactions it
JOIN companies c ON c.id = it.company_id
LEFT JOIN insiders i ON i.id = it.insider_id
LEFT JOIN insider_signal_scores iss ON iss.transaction_id = it.id
ORDER BY it.transaction_date DESC;

-- Top insider signals (today + recent)
CREATE VIEW top_insider_signals AS
SELECT
    it.id AS transaction_id,
    c.ticker,
    c.name AS company_name,
    c.sector,
    i.name AS insider_name,
    i.role AS insider_role,
    it.transaction_date,
    it.transaction_type,
    it.shares,
    it.price,
    it.transaction_value,
    it.ownership_change_pct,
    iss.score AS signal_score,
    iss.cluster_flag,
    iss.insider_skill_score,
    iss.signal_reason
FROM insider_transactions it
JOIN companies c ON c.id = it.company_id
LEFT JOIN insiders i ON i.id = it.insider_id
LEFT JOIN insider_signal_scores iss ON iss.transaction_id = it.id
WHERE it.transaction_type IN ('Buy', 'Purchase')
  AND iss.score IS NOT NULL
ORDER BY iss.score DESC, it.transaction_date DESC;

-- Institutional net accumulation by company
CREATE VIEW institutional_net_accumulation AS
SELECT
    company_id,
    quarter,
    SUM(CASE WHEN change_shares > 0 THEN change_shares ELSE 0 END) AS shares_bought,
    SUM(CASE WHEN change_shares < 0 THEN ABS(change_shares) ELSE 0 END) AS shares_sold,
    SUM(change_shares) AS net_change,
    COUNT(*) AS num_holders,
    COUNT(CASE WHEN change_shares > 0 THEN 1 END) AS num_buyers,
    COUNT(CASE WHEN change_shares < 0 THEN 1 END) AS num_sellers
FROM institutional_holdings
GROUP BY company_id, quarter;
