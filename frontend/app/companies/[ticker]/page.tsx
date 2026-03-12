"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getCompanySummary, getCompanyInsiders, getCompanyOwnership,
  getCompositeHistory, getCompanyMetrics, getMetricSeries,
  type Company, type InsiderTransaction, type CompositeScore, type CompanyOwnership,
} from "@/lib/api";
import { SignalTable } from "@/components/ui/SignalTable";
import { ScoreBadge, ScoreBar } from "@/components/ui/ScoreBadge";
import { SingleMetricChart } from "@/components/charts/MetricLineChart";
import { StatCard } from "@/components/ui/StatCard";
import { formatCurrency, formatDate, formatPercent, SECTOR_COLORS, cn } from "@/lib/utils";
import {
  ArrowLeft, ExternalLink, TrendingUp, Users, BarChart3,
  Activity, Building2, ChevronDown, ChevronRight,
} from "lucide-react";

type Tab = "overview" | "insiders" | "metrics" | "institutional" | "signals";

// Company-specific metric configs
const COMPANY_METRICS: Record<string, { name: string; metrics: string[] }> = {
  TSLA: {
    name: "Tesla Operational Metrics",
    metrics: [
      "tsla_vehicle_deliveries", "tsla_vehicle_production",
      "tsla_supercharger_sites", "tsla_battery_storage_gwh",
      "tsla_solar_deployed_mw", "tsla_automotive_gross_margin",
    ],
  },
  NVDA: {
    name: "NVIDIA AI Infrastructure",
    metrics: [
      "nvda_datacenter_revenue", "nvda_gaming_revenue",
      "nvda_gross_margin", "nvda_cuda_developers",
      "nvda_data_center_backlog",
    ],
  },
  AAPL: {
    name: "Apple Ecosystem Metrics",
    metrics: [
      "aapl_iphone_units", "aapl_services_revenue",
      "aapl_installed_base", "aapl_services_margin",
      "aapl_iphone_revenue", "aapl_china_revenue",
    ],
  },
  AMZN: {
    name: "Amazon Business Metrics",
    metrics: [
      "amzn_aws_revenue", "amzn_aws_growth_yoy",
      "amzn_prime_subscribers", "amzn_advertising_revenue",
      "amzn_fulfillment_centers",
    ],
  },
  MSFT: {
    name: "Microsoft Cloud Metrics",
    metrics: [
      "msft_azure_growth", "msft_cloud_revenue",
      "msft_office_commercial_seats", "msft_copilot_seats",
      "msft_ai_capex",
    ],
  },
  GOOGL: {
    name: "Alphabet Business Metrics",
    metrics: [
      "googl_search_revenue", "googl_youtube_revenue",
      "googl_cloud_revenue", "googl_cloud_growth",
      "googl_gemini_users",
    ],
  },
  META: {
    name: "Meta Platform Metrics",
    metrics: [
      "meta_dau", "meta_mau",
      "meta_arpu", "meta_ai_capex",
      "meta_reality_labs_revenue", "meta_threads_mau",
    ],
  },
};

function MetricCard({
  metricName,
  ticker,
  displayName,
  unit,
}: {
  metricName: string;
  ticker: string;
  displayName?: string;
  unit?: string;
}) {
  const [series, setSeries] = useState<{ date: string; value?: number }[]>([]);
  const [latest, setLatest] = useState<number | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    getMetricSeries(ticker, metricName, 5)
      .then((data) => {
        setSeries(data);
        const last = [...data].reverse().find((d) => d.value != null);
        setLatest(last?.value ?? null);
      })
      .catch(() => {});
  }, [ticker, metricName]);

  const label = displayName || metricName.replace(/_/g, " ").replace(/^[a-z]+_/, "");

  const formatVal = (v: number | null) => {
    if (v == null) return "—";
    if (Math.abs(v) >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
    if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
    if (Math.abs(v) >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
    return v.toFixed(1);
  };

  return (
    <div className="bg-surface-2 border border-surface-border rounded-xl overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-3 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className="text-left">
            <div className="text-sm font-medium text-text-primary capitalize">{label}</div>
            <div className="text-xs text-text-muted">{unit}</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold font-mono text-accent-blue">
            {formatVal(latest)}
            {unit === "%" && latest != null ? "%" : ""}
          </span>
          {expanded ? <ChevronDown size={14} className="text-text-muted" /> : <ChevronRight size={14} className="text-text-muted" />}
        </div>
      </button>
      {expanded && (
        <div className="px-4 pb-4">
          <SingleMetricChart
            data={series}
            label={label}
            unit={unit}
            color="#3b82f6"
            height={160}
          />
        </div>
      )}
    </div>
  );
}

export default function CompanyPage() {
  const { ticker } = useParams<{ ticker: string }>();
  const [summary, setSummary] = useState<{ company: Company; composite_score: CompositeScore; recent_trades: InsiderTransaction[]; key_metrics: unknown[] } | null>(null);
  const [transactions, setTransactions] = useState<InsiderTransaction[]>([]);
  const [ownership, setOwnership] = useState<CompanyOwnership | null>(null);
  const [scoreHistory, setScoreHistory] = useState<CompositeScore[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);

    Promise.all([
      getCompanySummary(ticker),
      getCompanyInsiders(ticker, 365),
    ])
      .then(([sum, trades]) => {
        setSummary(sum);
        setTransactions(trades);
      })
      .catch(console.error)
      .finally(() => setLoading(false));

    getCompanyOwnership(ticker).then(setOwnership).catch(() => {});
    getCompositeHistory(ticker).then(setScoreHistory).catch(() => {});
  }, [ticker]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-text-muted">
        <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mr-3" />
        Loading {ticker}...
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="text-center py-16 text-text-muted">
        <p className="text-lg">Company &quot;{ticker}&quot; not found</p>
        <Link href="/companies" className="text-accent-blue hover:underline mt-2 inline-block">
          ← Back to companies
        </Link>
      </div>
    );
  }

  const company = summary.company;
  const score = summary.composite_score;
  const sectorColor = SECTOR_COLORS[company.sector || ""] || "#3b82f6";
  const companyMetricConfig = COMPANY_METRICS[ticker.toUpperCase()];

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "overview", label: "Overview", icon: <Building2 size={13} /> },
    { id: "insiders", label: `Insider Trades (${transactions.length})`, icon: <Users size={13} /> },
    { id: "metrics", label: "KPI Metrics", icon: <Activity size={13} /> },
    { id: "institutional", label: "Institutional", icon: <BarChart3 size={13} /> },
  ];

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Back */}
      <Link href="/companies" className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors">
        <ArrowLeft size={14} />
        All Companies
      </Link>

      {/* Company Header */}
      <div className="bg-surface-1 border border-surface-border rounded-xl p-5">
        <div className="flex items-start gap-5">
          {/* Logo placeholder */}
          <div
            className="w-14 h-14 rounded-xl flex items-center justify-center text-xl font-bold"
            style={{ backgroundColor: `${sectorColor}20`, border: `1px solid ${sectorColor}40`, color: sectorColor }}
          >
            {ticker.slice(0, 2)}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold font-mono text-text-primary">{ticker}</h1>
                  <span className="text-xl text-text-muted">{company.name}</span>
                </div>
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  <span
                    className="text-xs px-2 py-0.5 rounded-full"
                    style={{ backgroundColor: `${sectorColor}20`, color: sectorColor }}
                  >
                    {company.sector}
                  </span>
                  <span className="text-xs text-text-muted">{company.industry}</span>
                  <span className="text-xs text-text-muted">·</span>
                  <span className="text-xs text-text-muted">{company.exchange}</span>
                  <span className="text-xs text-text-muted font-mono">
                    MktCap: {formatCurrency(company.market_cap, true)}
                  </span>
                </div>
              </div>
              <div className="shrink-0">
                <ScoreBadge score={score?.composite_score} size="lg" label="Score" />
              </div>
            </div>
          </div>
        </div>

        {/* Score breakdown */}
        {score && (
          <div className="mt-4 pt-4 border-t border-surface-border grid grid-cols-2 md:grid-cols-4 gap-4">
            <ScoreBar score={score.insider_score} label="Insider Conviction" />
            <ScoreBar score={score.institutional_score} label="Institutional" />
            <ScoreBar score={score.business_momentum_score} label="Business Momentum" />
            <ScoreBar score={score.industry_score} label="Industry Expansion" />
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label="Composite Score"
          value={score?.composite_score?.toFixed(1) || "—"}
          accent="blue"
        />
        <StatCard
          label="Insider Alignment"
          value={score?.insider_alignment?.toFixed(1) || "—"}
          sub="Insiders + Institutions"
          accent="green"
        />
        <StatCard
          label="Recent Buys (30d)"
          value={transactions.filter(t => t.transaction_type.toLowerCase().includes("buy") &&
            new Date(t.transaction_date) > new Date(Date.now() - 30 * 864e5)).length}
          accent="cyan"
        />
        <StatCard
          label="Inst. Ownership"
          value={ownership?.institutional_ownership_pct
            ? `${ownership.institutional_ownership_pct.toFixed(1)}%`
            : "—"}
          sub={`${ownership?.num_holders || "—"} holders`}
          accent="amber"
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-surface-border">
        <div className="flex gap-0">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                "flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
                tab === t.id
                  ? "border-accent-blue text-accent-blue"
                  : "border-transparent text-text-muted hover:text-text-secondary"
              )}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="animate-slide-up">
        {tab === "overview" && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            {/* Recent trades */}
            <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
              <div className="px-5 py-3 border-b border-surface-border flex items-center justify-between">
                <span className="text-sm font-semibold text-text-primary">Recent Insider Trades</span>
                <button onClick={() => setTab("insiders")} className="text-xs text-accent-blue hover:underline">
                  See all
                </button>
              </div>
              <SignalTable signals={transactions.slice(0, 8) as unknown as Parameters<typeof SignalTable>[0]["signals"]} showCompany={false} compact />
            </div>

            {/* Key metrics preview */}
            {companyMetricConfig ? (
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-text-primary">{companyMetricConfig.name}</h3>
                {companyMetricConfig.metrics.slice(0, 4).map((m) => (
                  <MetricCard key={m} metricName={m} ticker={ticker.toUpperCase()} />
                ))}
              </div>
            ) : (
              <div className="bg-surface-1 border border-surface-border rounded-xl p-5 space-y-3">
                <h3 className="text-sm font-semibold text-text-primary">Key Financial Metrics</h3>
                {["revenue", "gross_margin", "free_cash_flow", "eps_diluted"].map((m) => (
                  <MetricCard key={m} metricName={m} ticker={ticker.toUpperCase()} />
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "insiders" && (
          <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-surface-border">
              <span className="text-sm font-semibold text-text-primary">All Insider Transactions (12 months)</span>
            </div>
            <SignalTable signals={transactions as unknown as Parameters<typeof SignalTable>[0]["signals"]} showCompany={false} />
          </div>
        )}

        {tab === "metrics" && (
          <div className="space-y-3">
            <div className="text-sm text-text-muted">
              Operational KPIs sourced from earnings reports, EDGAR filings, and investor presentations.
            </div>
            {companyMetricConfig
              ? companyMetricConfig.metrics.map((m) => (
                  <MetricCard key={m} metricName={m} ticker={ticker.toUpperCase()} />
                ))
              : ["revenue", "gross_margin", "operating_income", "free_cash_flow", "eps_diluted", "capex", "headcount", "r_and_d_spend"].map((m) => (
                  <MetricCard key={m} metricName={m} ticker={ticker.toUpperCase()} />
                ))}
          </div>
        )}

        {tab === "institutional" && ownership && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="Total Inst. Shares" value={ownership.total_institutional_shares
                ? `${(ownership.total_institutional_shares / 1e6).toFixed(0)}M` : "—"} accent="blue" />
              <StatCard label="Ownership %" value={ownership.institutional_ownership_pct
                ? `${ownership.institutional_ownership_pct.toFixed(1)}%` : "—"} accent="green" />
              <StatCard label="# Holders" value={ownership.num_holders || "—"} accent="cyan" />
              <StatCard label="Accum. Score" value={ownership.accumulation_score?.toFixed(1) || "—"} accent="amber" />
            </div>

            <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
              <div className="px-5 py-3 border-b border-surface-border">
                <span className="text-sm font-semibold text-text-primary">Top Institutional Holders</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-surface-border">
                      <th className="text-left py-2 px-4 text-xs text-text-muted">Institution</th>
                      <th className="text-left py-2 px-4 text-xs text-text-muted">Type</th>
                      <th className="text-right py-2 px-4 text-xs text-text-muted">Shares</th>
                      <th className="text-right py-2 px-4 text-xs text-text-muted">Value</th>
                      <th className="text-right py-2 px-4 text-xs text-text-muted">Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ownership.top_holders.map((h, i) => (
                      <tr key={i} className="border-b border-surface-border/50 hover:bg-surface-2/50">
                        <td className="py-2.5 px-4 text-text-primary font-medium text-xs">{h.firm_name}</td>
                        <td className="py-2.5 px-4 text-text-muted text-xs">{h.firm_type}</td>
                        <td className="py-2.5 px-4 text-right font-mono text-xs text-text-secondary">
                          {h.shares ? `${(h.shares / 1e6).toFixed(1)}M` : "—"}
                        </td>
                        <td className="py-2.5 px-4 text-right font-mono text-xs text-text-secondary">
                          {formatCurrency(h.value, true)}
                        </td>
                        <td className="py-2.5 px-4 text-right font-mono text-xs">
                          {h.change_pct != null ? (
                            <span className={h.change_pct > 0 ? "text-accent-green" : "text-accent-red"}>
                              {h.change_pct > 0 ? "+" : ""}{h.change_pct.toFixed(1)}%
                            </span>
                          ) : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
