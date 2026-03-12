/**
 * FINTEL API Client
 * Typed wrapper around the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type TransactionType = "Buy" | "Sell" | "Award" | "Exercise" | string;

export interface Company {
  id: number;
  ticker: string;
  name: string;
  sector?: string;
  industry?: string;
  market_cap?: number;
  exchange?: string;
  logo_url?: string;
  composite_score?: number;
  insider_score?: number;
  institutional_score?: number;
  business_momentum_score?: number;
}

export interface InsiderTransaction {
  id: number;
  company_id: number;
  insider_id?: number;
  ticker?: string;
  company_name?: string;
  insider_name?: string;
  insider_role?: string;
  transaction_date: string;
  transaction_type: TransactionType;
  shares: number;
  price?: number;
  transaction_value?: number;
  ownership_change_pct?: number;
  filing_type?: string;
  filing_url?: string;
  signal_score?: number;
  cluster_flag?: boolean;
}

export interface TopSignal extends InsiderTransaction {
  signal_reason?: string;
  insider_skill_score?: number;
  sector?: string;
}

export interface CompositeScore {
  company_id: number;
  ticker: string;
  company_name: string;
  sector?: string;
  date: string;
  insider_score?: number;
  institutional_score?: number;
  business_momentum_score?: number;
  industry_score?: number;
  composite_score?: number;
  insider_alignment?: number;
  buys_30d?: number;
  market_cap?: number;
}

export interface ClusterEvent {
  id: number;
  company_id: number;
  ticker: string;
  company_name: string;
  start_date: string;
  end_date: string;
  insider_count: number;
  total_value?: number;
  cluster_score?: number;
  sector?: string;
}

export interface DashboardData {
  top_signals: TopSignal[];
  top_composite_scores: CompositeScore[];
  recent_cluster_events: ClusterEvent[];
  total_transactions_today: number;
  total_buy_value_today: number;
  market_date: string;
}

export interface MetricDef {
  id: number;
  name: string;
  display_name?: string;
  category: string;
  subcategory?: string;
  unit?: string;
  description?: string;
  frequency?: string;
}

export interface MetricValue {
  date: string;
  value?: number;
  yoy_growth?: number;
  source?: string;
}

export interface MetricSeries {
  company_id: number;
  ticker: string;
  company_name: string;
  values: MetricValue[];
}

export interface MetricComparison {
  metric: MetricDef;
  companies: MetricSeries[];
}

export interface InstitutionalHolder {
  firm_name: string;
  firm_type?: string;
  quarter: string;
  shares?: number;
  value?: number;
  change_shares?: number;
  change_pct?: number;
}

export interface CompanyOwnership {
  company_id: number;
  ticker: string;
  total_institutional_shares?: number;
  institutional_ownership_pct?: number;
  num_holders?: number;
  top_holders: InstitutionalHolder[];
  net_change_last_quarter?: number;
  accumulation_score?: number;
}

export interface SectorHeatmap {
  sector: string;
  total_trades: number;
  buys: number;
  sells: number;
  total_buy_value: number;
  total_sell_value: number;
  avg_signal_score: number;
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

// ---- Dashboard ----
export const getDashboard = () => fetchApi<DashboardData>("/api/dashboard");
export const getTopSignals = (days = 30, minScore = 5, limit = 50) =>
  fetchApi<TopSignal[]>(`/api/dashboard/signals/top?days=${days}&min_score=${minScore}&limit=${limit}`);

// ---- Companies ----
export const getCompanies = (params?: { sector?: string; search?: string; limit?: number }) => {
  const q = new URLSearchParams();
  if (params?.sector) q.set("sector", params.sector);
  if (params?.search) q.set("search", params.search);
  if (params?.limit) q.set("limit", String(params.limit));
  return fetchApi<Company[]>(`/api/companies?${q}`);
};
export const getCompany = (ticker: string) =>
  fetchApi<Company>(`/api/companies/${ticker}`);
export const getCompanySummary = (ticker: string) =>
  fetchApi<{ company: Company; composite_score: CompositeScore; recent_trades: InsiderTransaction[]; key_metrics: unknown[] }>(`/api/companies/${ticker}/summary`);
export const getSectors = () => fetchApi<string[]>("/api/companies/sectors");

// ---- Insiders ----
export const getTransactions = (params?: {
  ticker?: string; days?: number; min_value?: number;
  transaction_type?: string; limit?: number;
}) => {
  const q = new URLSearchParams();
  if (params?.ticker) q.set("ticker", params.ticker);
  if (params?.days) q.set("days", String(params.days));
  if (params?.min_value) q.set("min_value", String(params.min_value));
  if (params?.transaction_type) q.set("transaction_type", params.transaction_type);
  if (params?.limit) q.set("limit", String(params.limit));
  return fetchApi<InsiderTransaction[]>(`/api/insiders/transactions?${q}`);
};
export const getCompanyInsiders = (ticker: string, days = 365) =>
  fetchApi<InsiderTransaction[]>(`/api/insiders/company/${ticker}?days=${days}`);
export const getClusterEvents = (days = 90) =>
  fetchApi<ClusterEvent[]>(`/api/insiders/clusters/recent?days=${days}`);

// ---- Signals ----
export const getSectorHeatmap = (days = 30) =>
  fetchApi<SectorHeatmap[]>(`/api/signals/sector-heatmap?days=${days}`);
export const getConvictionTimeline = (ticker?: string, days = 365) => {
  const q = new URLSearchParams({ days: String(days) });
  if (ticker) q.set("ticker", ticker);
  return fetchApi<unknown[]>(`/api/signals/conviction-timeline?${q}`);
};

// ---- Metrics ----
export const getMetrics = (category?: string) => {
  const q = category ? `?category=${category}` : "";
  return fetchApi<MetricDef[]>(`/api/metrics${q}`);
};
export const getMetricCategories = () => fetchApi<string[]>("/api/metrics/categories");
export const getCompanyMetrics = (ticker: string, category?: string) => {
  const q = category ? `?category=${category}` : "";
  return fetchApi<unknown[]>(`/api/metrics/company/${ticker}${q}`);
};
export const getMetricSeries = (ticker: string, metricName: string, years = 5) =>
  fetchApi<MetricValue[]>(`/api/metrics/company/${ticker}/${metricName}/series?limit_years=${years}`);
export const compareMetric = (metricName: string, tickers: string[], years = 5) =>
  fetchApi<MetricComparison>(`/api/metrics/${metricName}/compare?tickers=${tickers.join(",")}&limit_years=${years}`);

// ---- Institutional ----
export const getCompanyOwnership = (ticker: string) =>
  fetchApi<CompanyOwnership>(`/api/institutional/company/${ticker}`);
export const getNetAccumulation = (sector?: string) => {
  const q = sector ? `?sector=${sector}` : "";
  return fetchApi<unknown[]>(`/api/institutional/net-accumulation${q}`);
};

// ---- Composite ----
export const getLeaderboard = (sector?: string, sortBy?: string) => {
  const q = new URLSearchParams();
  if (sector) q.set("sector", sector);
  if (sortBy) q.set("sort_by", sortBy);
  return fetchApi<CompositeScore[]>(`/api/composite/leaderboard?${q}`);
};
export const getCompositeHistory = (ticker: string) =>
  fetchApi<CompositeScore[]>(`/api/composite/score/${ticker}`);
