-- ============================================================
-- FINTEL: Seed Data
-- Migration 002: S&P 500 Core Companies + Metrics Registry
-- ============================================================

-- ============================================================
-- S&P 500 REPRESENTATIVE COMPANIES
-- ============================================================
INSERT INTO companies (ticker, name, sector, industry, market_cap, cik, exchange) VALUES
-- Technology
('AAPL',  'Apple Inc.',                          'Technology',       'Consumer Electronics',      3000000000000, '0000320193', 'NASDAQ'),
('MSFT',  'Microsoft Corporation',               'Technology',       'Software',                  3100000000000, '0000789019', 'NASDAQ'),
('NVDA',  'NVIDIA Corporation',                  'Technology',       'Semiconductors',            2800000000000, '0001045810', 'NASDAQ'),
('GOOGL', 'Alphabet Inc.',                       'Technology',       'Internet Services',         2100000000000, '0001652044', 'NASDAQ'),
('META',  'Meta Platforms Inc.',                 'Technology',       'Social Media',               1400000000000, '0001326801', 'NASDAQ'),
('AVGO',  'Broadcom Inc.',                       'Technology',       'Semiconductors',             800000000000, '0001730168', 'NASDAQ'),
('ORCL',  'Oracle Corporation',                  'Technology',       'Software',                   490000000000, '0001341439', 'NYSE'),
('AMD',   'Advanced Micro Devices Inc.',         'Technology',       'Semiconductors',             240000000000, '0000002488', 'NASDAQ'),
('INTC',  'Intel Corporation',                   'Technology',       'Semiconductors',             100000000000, '0000050863', 'NASDAQ'),
('QCOM',  'Qualcomm Incorporated',               'Technology',       'Semiconductors',             180000000000, '0000804328', 'NASDAQ'),
('CRM',   'Salesforce Inc.',                     'Technology',       'Software',                   300000000000, '0001108524', 'NYSE'),
('ADBE',  'Adobe Inc.',                          'Technology',       'Software',                   220000000000, '0000796343', 'NASDAQ'),
('NOW',   'ServiceNow Inc.',                     'Technology',       'Software',                   200000000000, '0001373715', 'NYSE'),
('PLTR',  'Palantir Technologies Inc.',          'Technology',       'Software',                   160000000000, '0001321655', 'NYSE'),
('SNOW',  'Snowflake Inc.',                      'Technology',       'Software',                    55000000000, '0001640147', 'NYSE'),

-- Consumer Discretionary
('AMZN',  'Amazon.com Inc.',                     'Consumer Discretionary', 'E-Commerce',          1900000000000, '0001018724', 'NASDAQ'),
('TSLA',  'Tesla Inc.',                          'Consumer Discretionary', 'Electric Vehicles',    700000000000, '0001318605', 'NASDAQ'),
('HD',    'The Home Depot Inc.',                 'Consumer Discretionary', 'Home Improvement',     395000000000, '0000354950', 'NYSE'),
('MCD',   'McDonald''s Corporation',             'Consumer Discretionary', 'Restaurants',          215000000000, '0000063754', 'NYSE'),
('NKE',   'Nike Inc.',                           'Consumer Discretionary', 'Apparel',               80000000000, '0000320187', 'NYSE'),

-- Financials
('BRK',   'Berkshire Hathaway Inc.',             'Financials',       'Diversified',               900000000000, '0001067983', 'NYSE'),
('JPM',   'JPMorgan Chase & Co.',                'Financials',       'Banks',                      680000000000, '0000019617', 'NYSE'),
('V',     'Visa Inc.',                           'Financials',       'Payments',                   580000000000, '0001403161', 'NYSE'),
('MA',    'Mastercard Incorporated',             'Financials',       'Payments',                   490000000000, '0001141391', 'NYSE'),
('GS',    'The Goldman Sachs Group Inc.',        'Financials',       'Investment Banking',         175000000000, '0000886982', 'NYSE'),

-- Healthcare
('LLY',   'Eli Lilly and Company',              'Healthcare',       'Pharmaceuticals',             800000000000, '0000059478', 'NYSE'),
('UNH',   'UnitedHealth Group Incorporated',    'Healthcare',       'Health Insurance',            500000000000, '0000731766', 'NYSE'),
('JNJ',   'Johnson & Johnson',                  'Healthcare',       'Diversified Healthcare',      370000000000, '0000200406', 'NYSE'),
('ABBV',  'AbbVie Inc.',                        'Healthcare',       'Pharmaceuticals',             310000000000, '0001551152', 'NYSE'),
('MRK',   'Merck & Co. Inc.',                   'Healthcare',       'Pharmaceuticals',             280000000000, '0000310158', 'NYSE'),

-- Energy
('XOM',   'Exxon Mobil Corporation',            'Energy',           'Oil & Gas',                   490000000000, '0000034088', 'NYSE'),
('CVX',   'Chevron Corporation',                'Energy',           'Oil & Gas',                   280000000000, '0000093410', 'NYSE'),
('NEE',   'NextEra Energy Inc.',                'Energy',           'Utilities',                   150000000000, '0000753308', 'NYSE'),

-- Communication Services
('NFLX',  'Netflix Inc.',                       'Communication Services', 'Streaming',             350000000000, '0001065280', 'NASDAQ'),
('DIS',   'The Walt Disney Company',            'Communication Services', 'Entertainment',         195000000000, '0001744489', 'NYSE'),

-- Industrials
('BA',    'The Boeing Company',                 'Industrials',      'Aerospace & Defense',         110000000000, '0000012927', 'NYSE'),
('CAT',   'Caterpillar Inc.',                   'Industrials',      'Machinery',                   180000000000, '0000018230', 'NYSE'),
('GE',    'GE Aerospace',                       'Industrials',      'Aerospace & Defense',         215000000000, '0000040987', 'NYSE'),

-- Materials
('LIN',   'Linde plc',                          'Materials',        'Industrial Gases',            230000000000, '0001707092', 'NYSE'),

-- Real Estate
('AMT',   'American Tower Corporation',         'Real Estate',      'REITs',                       95000000000, '0001053507', 'NYSE');

-- ============================================================
-- METRIC REGISTRY
-- ============================================================
INSERT INTO metrics (name, display_name, category, subcategory, unit, description, source, frequency) VALUES

-- ---- TESLA METRICS ----
('tsla_supercharger_sites',        'Supercharger Sites',             'infrastructure', 'ev_charging',  'count', 'Number of Tesla Supercharger stations globally', 'earnings', 'quarterly'),
('tsla_supercharger_connectors',   'Supercharger Connectors',        'infrastructure', 'ev_charging',  'count', 'Total number of individual Supercharger connectors', 'earnings', 'quarterly'),
('tsla_vehicle_deliveries',        'Vehicle Deliveries',             'production',     'ev',            'count', 'Total Tesla vehicles delivered in the period', 'earnings', 'quarterly'),
('tsla_vehicle_production',        'Vehicle Production',             'production',     'ev',            'count', 'Total Tesla vehicles produced in the period', 'earnings', 'quarterly'),
('tsla_battery_storage_gwh',       'Battery Storage Deployed (GWh)', 'production',     'energy',        'GWh',   'Tesla energy storage products deployed (GWh)', 'earnings', 'quarterly'),
('tsla_solar_deployed_mw',         'Solar Deployed (MW)',            'production',     'energy',        'MW',    'Tesla solar panels and roof deployed (MW)', 'earnings', 'quarterly'),
('tsla_energy_revenue',            'Energy Revenue',                 'financial',      'revenue',       '$M',    'Revenue from Tesla Energy division', 'earnings', 'quarterly'),
('tsla_automotive_gross_margin',   'Auto Gross Margin',              'financial',      'margins',       '%',     'Automotive segment gross margin', 'earnings', 'quarterly'),
('tsla_fsd_take_rate',             'FSD Take Rate',                  'product',        'software',      '%',     'Percentage of buyers choosing FSD', 'estimates', 'quarterly'),
('tsla_model_y_share',             'Model Y Share of Deliveries',    'product',        'mix',           '%',     'Model Y as % of total deliveries', 'earnings', 'quarterly'),

-- ---- NVIDIA METRICS ----
('nvda_datacenter_revenue',        'Datacenter Revenue',             'financial',      'revenue',       '$M',    'NVIDIA datacenter segment revenue', 'earnings', 'quarterly'),
('nvda_gaming_revenue',            'Gaming Revenue',                 'financial',      'revenue',       '$M',    'NVIDIA gaming segment revenue', 'earnings', 'quarterly'),
('nvda_gpu_shipments',             'AI GPU Shipments (est.)',         'production',     'semiconductors','count', 'Estimated H100/A100 GPU units shipped', 'estimates', 'quarterly'),
('nvda_ai_capex_customer',         'Customer AI Capex ($B)',          'infrastructure', 'ai',            '$B',    'Combined AI capex of NVIDIA''s top customers', 'estimates', 'quarterly'),
('nvda_gross_margin',              'Gross Margin',                   'financial',      'margins',       '%',     'NVIDIA overall gross margin', 'earnings', 'quarterly'),
('nvda_data_center_backlog',       'Datacenter Order Backlog',        'production',     'demand',        '$B',    'Estimated datacenter order backlog', 'estimates', 'quarterly'),
('nvda_cuda_developers',           'CUDA Developers (M)',             'product',        'ecosystem',     'M',     'Number of CUDA-registered developers (millions)', 'investor_day', 'annual'),
('nvda_inference_revenue_share',   'Inference Revenue Share',         'product',        'mix',           '%',     'Inference workload as % of datacenter revenue', 'earnings', 'quarterly'),

-- ---- AMAZON METRICS ----
('amzn_aws_revenue',               'AWS Revenue',                    'financial',      'revenue',       '$M',    'Amazon Web Services segment revenue', 'earnings', 'quarterly'),
('amzn_aws_growth_yoy',            'AWS YoY Growth',                 'financial',      'growth',        '%',     'AWS revenue year-over-year growth', 'earnings', 'quarterly'),
('amzn_aws_operating_income',      'AWS Operating Income',           'financial',      'profitability', '$M',    'AWS operating income', 'earnings', 'quarterly'),
('amzn_prime_subscribers',         'Prime Subscribers (M)',           'product',        'subscriptions', 'M',     'Amazon Prime subscribers worldwide', 'earnings', 'annual'),
('amzn_fulfillment_centers',       'Fulfillment Centers',            'infrastructure', 'logistics',     'count', 'Total Amazon fulfillment center count', 'earnings', 'annual'),
('amzn_advertising_revenue',       'Advertising Revenue',            'financial',      'revenue',       '$M',    'Amazon advertising services revenue', 'earnings', 'quarterly'),
('amzn_third_party_seller_pct',    'Third-Party Seller Share',        'product',        'mix',           '%',     'Third-party unit share of total Amazon', 'earnings', 'annual'),
('amzn_aws_datacenters',           'AWS Datacenter Regions',         'infrastructure', 'cloud',         'count', 'Number of AWS infrastructure regions', 'aws_site', 'quarterly'),
('amzn_capex',                     'Capital Expenditures',           'financial',      'capex',         '$B',    'Amazon total capital expenditures', 'earnings', 'quarterly'),

-- ---- APPLE METRICS ----
('aapl_iphone_units',              'iPhone Units Sold (M)',           'production',     'devices',       'M',     'iPhone units sold in the period', 'earnings', 'quarterly'),
('aapl_ipad_units',                'iPad Units Sold (M)',             'production',     'devices',       'M',     'iPad units sold in the period', 'earnings', 'quarterly'),
('aapl_mac_units',                 'Mac Units Sold (M)',              'production',     'devices',       'M',     'Mac units sold in the period', 'earnings', 'quarterly'),
('aapl_services_revenue',          'Services Revenue',               'financial',      'revenue',       '$M',    'Apple Services segment revenue', 'earnings', 'quarterly'),
('aapl_wearables_revenue',         'Wearables Revenue',              'financial',      'revenue',       '$M',    'Apple Wearables/Home/Accessories revenue', 'earnings', 'quarterly'),
('aapl_installed_base',            'Installed Active Device Base (B)','product',        'ecosystem',     'B',     'Total active Apple devices (billions)', 'earnings', 'annual'),
('aapl_app_store_accounts',        'App Store Accounts (M)',          'product',        'ecosystem',     'M',     'Active App Store accounts (millions)', 'estimates', 'annual'),
('aapl_services_margin',           'Services Gross Margin',          'financial',      'margins',       '%',     'Services segment gross margin', 'earnings', 'quarterly'),
('aapl_china_revenue',             'Greater China Revenue',          'financial',      'revenue',       '$M',    'Apple revenue from Greater China region', 'earnings', 'quarterly'),
('aapl_iphone_revenue',            'iPhone Revenue',                 'financial',      'revenue',       '$M',    'Apple iPhone segment revenue', 'earnings', 'quarterly'),

-- ---- MICROSOFT METRICS ----
('msft_azure_growth',              'Azure Revenue Growth (YoY)',       'financial',      'growth',        '%',     'Microsoft Azure year-over-year growth', 'earnings', 'quarterly'),
('msft_cloud_revenue',             'Intelligent Cloud Revenue',       'financial',      'revenue',       '$M',    'Microsoft Intelligent Cloud segment revenue', 'earnings', 'quarterly'),
('msft_office_commercial_seats',   'M365 Commercial Seats (M)',        'product',        'subscriptions', 'M',     'Microsoft 365 commercial seats (millions)', 'earnings', 'quarterly'),
('msft_gaming_revenue',            'Gaming Revenue',                  'financial',      'revenue',       '$M',    'Microsoft Gaming segment revenue', 'earnings', 'quarterly'),
('msft_copilot_seats',             'Copilot Enterprise Seats (M)',     'product',        'ai',            'M',     'Microsoft Copilot commercial seats (millions)', 'earnings', 'quarterly'),
('msft_linkedin_revenue',          'LinkedIn Revenue',                'financial',      'revenue',       '$M',    'LinkedIn revenue', 'earnings', 'quarterly'),
('msft_ai_capex',                  'AI Infrastructure Capex',         'infrastructure', 'ai',            '$B',    'Microsoft AI/cloud capex', 'earnings', 'quarterly'),
('msft_azure_openai_customers',    'Azure OpenAI Customers',          'product',        'ai',            'count', 'Enterprise customers using Azure OpenAI Service', 'earnings', 'quarterly'),

-- ---- ALPHABET (GOOGLE) METRICS ----
('googl_search_revenue',           'Search Revenue',                  'financial',      'revenue',       '$M',    'Google Search advertising revenue', 'earnings', 'quarterly'),
('googl_youtube_revenue',          'YouTube Revenue',                 'financial',      'revenue',       '$M',    'YouTube advertising revenue', 'earnings', 'quarterly'),
('googl_cloud_revenue',            'Google Cloud Revenue',            'financial',      'revenue',       '$M',    'Google Cloud Platform revenue', 'earnings', 'quarterly'),
('googl_cloud_growth',             'Google Cloud YoY Growth',         'financial',      'growth',        '%',     'Google Cloud year-over-year revenue growth', 'earnings', 'quarterly'),
('googl_tpu_deployments',          'TPU Pod Deployments (est.)',       'infrastructure', 'ai',            'count', 'Estimated Google TPU pod deployments', 'estimates', 'annual'),
('googl_waymo_trips',              'Waymo Trips (weekly)',             'product',        'autonomy',      'count', 'Weekly Waymo commercial trip count', 'investor_updates', 'quarterly'),
('googl_gemini_users',             'Gemini Monthly Users (M)',         'product',        'ai',            'M',     'Monthly active users of Gemini AI (millions)', 'earnings', 'quarterly'),

-- ---- META METRICS ----
('meta_dau',                       'Daily Active Users (B)',           'product',        'users',         'B',     'Meta family apps daily active users (billions)', 'earnings', 'quarterly'),
('meta_mau',                       'Monthly Active Users (B)',         'product',        'users',         'B',     'Meta family apps monthly active users (billions)', 'earnings', 'quarterly'),
('meta_arpu',                      'Average Revenue Per User',         'financial',      'monetization',  '$',     'Average revenue per user worldwide', 'earnings', 'quarterly'),
('meta_ai_capex',                  'AI Infrastructure Capex',          'infrastructure', 'ai',            '$B',    'Meta AI/datacenter capex', 'earnings', 'quarterly'),
('meta_reality_labs_revenue',      'Reality Labs Revenue',             'financial',      'revenue',       '$M',    'Meta Reality Labs (VR/AR) revenue', 'earnings', 'quarterly'),
('meta_llama_downloads',           'LLaMA Downloads (M)',              'product',        'ai',            'M',     'Total LLaMA model downloads (millions)', 'developer_conference', 'annual'),
('meta_threads_mau',               'Threads MAU (M)',                  'product',        'users',         'M',     'Threads app monthly active users (millions)', 'earnings', 'quarterly'),

-- ---- CROSS-INDUSTRY METRICS (AI INFRASTRUCTURE) ----
('ai_capex_total',                 'AI Capex ($B)',                    'infrastructure', 'ai',            '$B',    'Company total AI infrastructure capex', 'earnings', 'quarterly'),
('datacenter_capacity_mw',         'Datacenter Capacity (MW)',         'infrastructure', 'cloud',         'MW',    'Total owned/leased datacenter capacity (megawatts)', 'estimates', 'annual'),
('gpu_cluster_size_k',             'GPU Cluster Size (K)',             'infrastructure', 'ai',            'K',     'Total AI GPU count in thousands', 'estimates', 'quarterly'),
('renewable_energy_pct',           'Renewable Energy %',              'esg',            'energy',        '%',     'Percentage of operations on renewable energy', 'sustainability', 'annual'),
('r_and_d_spend',                  'R&D Spend',                       'financial',      'investment',    '$M',    'Total research and development expenditure', 'earnings', 'quarterly'),
('headcount',                      'Employee Headcount',              'operational',    'workforce',     'count', 'Total employee headcount', 'earnings', 'quarterly'),
('revenue_per_employee',           'Revenue Per Employee',            'operational',    'efficiency',    '$K',    'Annual revenue per employee (thousands)', 'calculated', 'annual'),

-- ---- EV ECOSYSTEM ----
('ev_deliveries_total',            'EV Deliveries (Global)',           'production',     'ev',            'count', 'Total EV deliveries globally', 'company_reports', 'quarterly'),
('charging_stations_public',       'Public Charging Stations',        'infrastructure', 'ev_charging',   'count', 'Number of public EV charging locations', 'government_data', 'quarterly'),
('battery_factory_gwh_capacity',   'Battery Factory Capacity (GWh)',  'infrastructure', 'batteries',     'GWh',   'Total global battery manufacturing capacity', 'company_reports', 'annual'),
('ev_market_share_pct',            'EV Market Share',                 'product',        'market_position','%',    'EV brand market share in total auto sales', 'industry', 'quarterly'),

-- ---- FINANCIAL METRICS (universal) ----
('revenue',                        'Revenue',                         'financial',      'revenue',       '$M',    'Total net revenue', 'earnings', 'quarterly'),
('gross_profit',                   'Gross Profit',                    'financial',      'profitability', '$M',    'Gross profit', 'earnings', 'quarterly'),
('gross_margin',                   'Gross Margin',                    'financial',      'margins',       '%',     'Gross margin percentage', 'earnings', 'quarterly'),
('operating_income',               'Operating Income',                'financial',      'profitability', '$M',    'Operating income (EBIT)', 'earnings', 'quarterly'),
('net_income',                     'Net Income',                      'financial',      'profitability', '$M',    'Net income attributable to common shareholders', 'earnings', 'quarterly'),
('eps_diluted',                    'Diluted EPS',                     'financial',      'earnings',      '$',     'Diluted earnings per share', 'earnings', 'quarterly'),
('free_cash_flow',                 'Free Cash Flow',                  'financial',      'cash',          '$M',    'Free cash flow (OCF - Capex)', 'earnings', 'quarterly'),
('capex',                          'Capital Expenditures',            'financial',      'investment',    '$M',    'Total capital expenditures', 'earnings', 'quarterly'),
('cash_equivalents',               'Cash & Equivalents',              'financial',      'balance_sheet', '$M',    'Cash and short-term investments', 'earnings', 'quarterly'),
('debt_total',                     'Total Debt',                      'financial',      'balance_sheet', '$M',    'Total long-term debt', 'earnings', 'quarterly'),
('shares_outstanding',             'Shares Outstanding (M)',          'financial',      'equity',        'M',     'Diluted shares outstanding (millions)', 'earnings', 'quarterly');

-- ============================================================
-- INSTITUTIONAL FIRMS SEED
-- ============================================================
INSERT INTO institutional_firms (name, cik, type, aum) VALUES
('BlackRock Inc.',                  '0001364742', 'Asset Manager',   10000000000000),
('Vanguard Group Inc.',             NULL,          'Asset Manager',    8000000000000),
('State Street Corporation',        '0000093751', 'Asset Manager',    4000000000000),
('Fidelity Management & Research',  NULL,          'Mutual Fund',      4500000000000),
('JPMorgan Asset Management',       NULL,          'Asset Manager',    3000000000000),
('T. Rowe Price Group Inc.',        '0001113169', 'Mutual Fund',      1500000000000),
('Berkshire Hathaway Inc.',         '0001067983', 'Hedge Fund',       1000000000000),
('Capital Group Companies',         NULL,          'Mutual Fund',      2200000000000),
('Geode Capital Management',        NULL,          'Quant',            1000000000000),
('Wellington Management',           NULL,          'Asset Manager',    1300000000000),
('Norges Bank Investment Mgmt',     NULL,          'Sovereign Wealth',  1700000000000),
('Invesco Ltd.',                    '0000914208', 'Asset Manager',     1600000000000),
('Morgan Stanley',                  '0000895421', 'Investment Bank',   700000000000),
('Goldman Sachs Asset Management',  '0000886982', 'Investment Bank',   500000000000),
('Citadel Advisors LLC',            NULL,          'Hedge Fund',        600000000000);
