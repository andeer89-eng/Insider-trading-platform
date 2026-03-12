import { type ClassValue, clsx } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatCurrency(value?: number | null, compact = false): string {
  if (value == null) return "—";
  if (compact) {
    if (Math.abs(value) >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
    if (Math.abs(value) >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
    return `$${value.toFixed(2)}`;
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatNumber(value?: number | null, decimals = 0): string {
  if (value == null) return "—";
  if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (Math.abs(value) >= 1e3) return `${(value / 1e3).toFixed(0)}K`;
  return value.toFixed(decimals);
}

export function formatPercent(value?: number | null, decimals = 1): string {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}%`;
}

export function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function scoreColor(score?: number | null): string {
  if (score == null) return "text-text-muted";
  if (score >= 8) return "text-accent-green";
  if (score >= 6) return "text-accent-cyan";
  if (score >= 4) return "text-accent-amber";
  return "text-accent-red";
}

export function scoreBg(score?: number | null): string {
  if (score == null) return "bg-surface-3";
  if (score >= 8) return "bg-accent-green/20 text-accent-green border border-accent-green/30";
  if (score >= 6) return "bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/30";
  if (score >= 4) return "bg-accent-amber/20 text-accent-amber border border-accent-amber/30";
  return "bg-accent-red/20 text-accent-red border border-accent-red/30";
}

export function txTypeColor(type?: string): string {
  if (!type) return "text-text-muted";
  const t = type.toLowerCase();
  if (t.includes("buy") || t.includes("purchase")) return "text-accent-green";
  if (t.includes("sell") || t.includes("sale")) return "text-accent-red";
  if (t.includes("award") || t.includes("grant")) return "text-accent-purple";
  if (t.includes("exercise")) return "text-accent-blue";
  return "text-text-secondary";
}

export function getLogoUrl(ticker: string): string {
  return `https://logo.clearbit.com/${tickerToDomain(ticker)}`;
}

function tickerToDomain(ticker: string): string {
  const map: Record<string, string> = {
    AAPL: "apple.com",
    MSFT: "microsoft.com",
    NVDA: "nvidia.com",
    GOOGL: "google.com",
    META: "meta.com",
    AMZN: "amazon.com",
    TSLA: "tesla.com",
    JPM: "jpmorganchase.com",
    V: "visa.com",
    MA: "mastercard.com",
    NFLX: "netflix.com",
    DIS: "disney.com",
    AMD: "amd.com",
    INTC: "intel.com",
    CRM: "salesforce.com",
    ADBE: "adobe.com",
    ORCL: "oracle.com",
    AVGO: "broadcom.com",
    NOW: "servicenow.com",
    PLTR: "palantir.com",
    SNOW: "snowflake.com",
    HD: "homedepot.com",
    MCD: "mcdonalds.com",
    NKE: "nike.com",
    LLY: "lilly.com",
    UNH: "unitedhealthgroup.com",
    JNJ: "jnj.com",
    XOM: "exxonmobil.com",
    CVX: "chevron.com",
    BA: "boeing.com",
    GE: "ge.com",
    CAT: "caterpillar.com",
    GS: "goldmansachs.com",
  };
  return map[ticker] || `${ticker.toLowerCase()}.com`;
}

export const SECTOR_COLORS: Record<string, string> = {
  Technology: "#3b82f6",
  "Consumer Discretionary": "#f59e0b",
  Financials: "#22c55e",
  Healthcare: "#a855f7",
  Energy: "#f97316",
  "Communication Services": "#06b6d4",
  Industrials: "#84cc16",
  Materials: "#ec4899",
  "Real Estate": "#14b8a6",
  Utilities: "#6366f1",
  "Consumer Staples": "#fb923c",
};

export const CHART_COLORS = [
  "#3b82f6", "#22c55e", "#f59e0b", "#a855f7",
  "#06b6d4", "#ef4444", "#84cc16", "#ec4899",
  "#14b8a6", "#f97316",
];
