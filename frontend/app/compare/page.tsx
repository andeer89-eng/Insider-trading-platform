"use client";
import { useEffect, useState, useCallback } from "react";
import { getMetrics, compareMetric, type MetricDef, type MetricComparison } from "@/lib/api";
import { MultiMetricChart } from "@/components/charts/MetricLineChart";
import { GitCompare, Plus, X, BarChart2 } from "lucide-react";
import { cn, CHART_COLORS } from "@/lib/utils";

const TICKER_SUGGESTIONS = [
  "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AAPL",
  "TSLA", "AMD", "INTC", "AVGO", "CRM", "ORCL",
];

const PRESET_COMPARISONS = [
  {
    label: "AI Infrastructure",
    metric: "ai_capex_total",
    tickers: ["NVDA", "MSFT", "AMZN", "GOOGL", "META"],
  },
  {
    label: "Cloud Revenue",
    metric: "amzn_aws_revenue",
    tickers: ["AMZN", "MSFT", "GOOGL"],
  },
  {
    label: "Datacenter Capacity",
    metric: "datacenter_capacity_mw",
    tickers: ["AMZN", "MSFT", "GOOGL", "META"],
  },
  {
    label: "Revenue Growth",
    metric: "revenue",
    tickers: ["NVDA", "META", "MSFT", "AAPL"],
  },
  {
    label: "R&D Spending",
    metric: "r_and_d_spend",
    tickers: ["MSFT", "GOOGL", "META", "AMZN"],
  },
  {
    label: "EV Deliveries",
    metric: "tsla_vehicle_deliveries",
    tickers: ["TSLA"],
  },
];

export default function ComparePage() {
  const [metrics, setMetrics] = useState<MetricDef[]>([]);
  const [selectedMetric, setSelectedMetric] = useState<string>("ai_capex_total");
  const [selectedTickers, setSelectedTickers] = useState<string[]>(["NVDA", "MSFT", "AMZN", "GOOGL", "META"]);
  const [tickerInput, setTickerInput] = useState("");
  const [comparisonData, setComparisonData] = useState<MetricComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [showGrowth, setShowGrowth] = useState(false);
  const [years, setYears] = useState(5);

  useEffect(() => {
    getMetrics().then(setMetrics).catch(console.error);
  }, []);

  const loadComparison = useCallback(() => {
    if (!selectedMetric || selectedTickers.length === 0) return;
    setLoading(true);
    compareMetric(selectedMetric, selectedTickers, years)
      .then(setComparisonData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedMetric, selectedTickers, years]);

  useEffect(() => {
    loadComparison();
  }, [loadComparison]);

  const addTicker = () => {
    const t = tickerInput.trim().toUpperCase();
    if (t && !selectedTickers.includes(t)) {
      setSelectedTickers([...selectedTickers, t]);
    }
    setTickerInput("");
  };

  const removeTicker = (t: string) => {
    setSelectedTickers(selectedTickers.filter((x) => x !== t));
  };

  const applyPreset = (preset: typeof PRESET_COMPARISONS[0]) => {
    setSelectedMetric(preset.metric);
    setSelectedTickers(preset.tickers);
  };

  const currentMetric = metrics.find((m) => m.name === selectedMetric);

  // Group metrics by category
  const metricGroups: Record<string, MetricDef[]> = {};
  metrics.forEach((m) => {
    if (!metricGroups[m.category]) metricGroups[m.category] = [];
    metricGroups[m.category].push(m);
  });

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
          <GitCompare size={22} className="text-accent-purple" />
          Cross-Company Metric Comparison
        </h1>
        <p className="text-text-muted text-sm mt-1">
          Compare operational KPIs across multiple companies on the same chart
        </p>
      </div>

      {/* Presets */}
      <div className="flex flex-wrap gap-2">
        <span className="text-xs text-text-muted py-1">Quick presets:</span>
        {PRESET_COMPARISONS.map((p) => (
          <button
            key={p.label}
            onClick={() => applyPreset(p)}
            className="px-3 py-1 bg-surface-2 border border-surface-border rounded-lg text-xs text-text-secondary hover:bg-surface-3 hover:text-text-primary transition-colors"
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Config panel */}
      <div className="bg-surface-1 border border-surface-border rounded-xl p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Metric selector */}
          <div>
            <label className="text-xs text-text-muted uppercase tracking-wider font-medium mb-2 block">
              Select Metric
            </label>
            <select
              value={selectedMetric}
              onChange={(e) => setSelectedMetric(e.target.value)}
              className="w-full bg-surface-2 border border-surface-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
            >
              <option value="">-- Choose a metric --</option>
              {Object.entries(metricGroups).map(([category, mets]) => (
                <optgroup key={category} label={category.toUpperCase()}>
                  {mets.map((m) => (
                    <option key={m.name} value={m.name}>
                      {m.display_name || m.name} {m.unit ? `(${m.unit})` : ""}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          {/* Company selector */}
          <div>
            <label className="text-xs text-text-muted uppercase tracking-wider font-medium mb-2 block">
              Companies
            </label>
            <div className="flex gap-2 mb-2">
              <input
                value={tickerInput}
                onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === "Enter" && addTicker()}
                placeholder="Add ticker..."
                className="flex-1 bg-surface-2 border border-surface-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue"
              />
              <button
                onClick={addTicker}
                className="px-3 py-2 bg-accent-blue text-white rounded-lg text-sm hover:bg-blue-600 transition-colors"
              >
                <Plus size={14} />
              </button>
            </div>

            {/* Selected tickers */}
            <div className="flex flex-wrap gap-1.5 mb-2">
              {selectedTickers.map((t, i) => (
                <span
                  key={t}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-mono font-semibold"
                  style={{ backgroundColor: `${CHART_COLORS[i % CHART_COLORS.length]}20`, color: CHART_COLORS[i % CHART_COLORS.length], border: `1px solid ${CHART_COLORS[i % CHART_COLORS.length]}30` }}
                >
                  {t}
                  <button onClick={() => removeTicker(t)} className="hover:opacity-70">
                    <X size={10} />
                  </button>
                </span>
              ))}
            </div>

            {/* Suggestions */}
            <div className="flex flex-wrap gap-1">
              {TICKER_SUGGESTIONS.filter(t => !selectedTickers.includes(t)).slice(0, 6).map((t) => (
                <button
                  key={t}
                  onClick={() => setSelectedTickers([...selectedTickers, t])}
                  className="px-2 py-0.5 text-xs font-mono bg-surface-3 text-text-muted hover:text-text-primary rounded transition-colors"
                >
                  + {t}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Options */}
        <div className="flex items-center gap-4 mt-4 pt-4 border-t border-surface-border">
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted">Years:</span>
            {[2, 3, 5, 10].map((y) => (
              <button
                key={y}
                onClick={() => setYears(y)}
                className={cn(
                  "px-2.5 py-1 rounded text-xs font-medium transition-colors",
                  years === y ? "bg-accent-blue text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
                )}
              >
                {y}y
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowGrowth(!showGrowth)}
              className={cn(
                "px-3 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1",
                showGrowth ? "bg-accent-cyan text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
              )}
            >
              <BarChart2 size={11} />
              YoY Growth
            </button>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-surface-border">
          <div className="text-sm font-semibold text-text-primary">
            {currentMetric?.display_name || selectedMetric}
          </div>
          {currentMetric?.description && (
            <div className="text-xs text-text-muted mt-0.5">{currentMetric.description}</div>
          )}
        </div>
        <div className="p-5">
          {loading ? (
            <div className="flex items-center justify-center h-64 text-text-muted text-sm">
              <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mr-3" />
              Loading comparison data...
            </div>
          ) : comparisonData ? (
            <MultiMetricChart
              companies={comparisonData.companies}
              unit={currentMetric?.unit}
              height={350}
              showGrowth={showGrowth}
            />
          ) : (
            <div className="flex items-center justify-center h-64 text-text-muted text-sm">
              Select a metric and companies to compare
            </div>
          )}
        </div>
      </div>

      {/* Data table */}
      {comparisonData && comparisonData.companies.length > 0 && (
        <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-surface-border">
            <span className="text-sm font-semibold text-text-primary">Latest Values</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border">
                  <th className="text-left py-2.5 px-4 text-xs text-text-muted">Company</th>
                  <th className="text-right py-2.5 px-4 text-xs text-text-muted">Latest</th>
                  <th className="text-right py-2.5 px-4 text-xs text-text-muted">YoY Growth</th>
                  <th className="text-right py-2.5 px-4 text-xs text-text-muted">Date</th>
                </tr>
              </thead>
              <tbody>
                {comparisonData.companies.map((company, i) => {
                  const latest = [...(company.values || [])].reverse().find((v) => v.value != null);
                  return (
                    <tr key={company.ticker} className="border-b border-surface-border/50">
                      <td className="py-2.5 px-4">
                        <span
                          className="font-mono font-semibold text-sm"
                          style={{ color: CHART_COLORS[i % CHART_COLORS.length] }}
                        >
                          {company.ticker}
                        </span>
                        <span className="text-text-muted text-xs ml-2">{company.company_name}</span>
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono text-text-primary text-sm">
                        {latest?.value != null
                          ? `${latest.value >= 1e6 ? (latest.value / 1e6).toFixed(1) + "M" : latest.value.toFixed(1)} ${currentMetric?.unit || ""}`
                          : "—"}
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono text-sm">
                        {latest?.yoy_growth != null ? (
                          <span className={latest.yoy_growth > 0 ? "text-accent-green" : "text-accent-red"}>
                            {latest.yoy_growth > 0 ? "+" : ""}{latest.yoy_growth.toFixed(1)}%
                          </span>
                        ) : "—"}
                      </td>
                      <td className="py-2.5 px-4 text-right text-text-muted text-xs font-mono">
                        {latest?.date || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
