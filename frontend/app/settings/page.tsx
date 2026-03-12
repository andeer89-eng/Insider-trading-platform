"use client";
import { useEffect, useState } from "react";
import { Settings, AlertCircle, CheckCircle, RefreshCw } from "lucide-react";

interface PipelineStatus {
  pipeline: string;
  status: string;
  last_run?: string;
  records_processed?: number;
  error?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SettingsPage() {
  const [pipelines, setPipelines] = useState<PipelineStatus[]>([]);
  const [health, setHealth] = useState<{ status: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      const [healthRes, pipelinesRes] = await Promise.all([
        fetch(`${API_BASE}/api/health`).then((r) => r.json()),
        fetch(`${API_BASE}/api/pipelines/status`).then((r) => r.json()),
      ]);
      setHealth(healthRes);
      setPipelines(pipelinesRes);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchStatus(); }, []);

  const triggerPipeline = async (name: string) => {
    await fetch(`${API_BASE}/api/pipelines/run/${name}`, { method: "POST" });
    setTimeout(fetchStatus, 2000);
  };

  const pipelineLabels: Record<string, string> = {
    sec_filings: "SEC Form 4 Filings",
    market_data: "Market Data & Returns",
    institutional_13f: "Institutional 13F Holdings",
    signal_scoring: "Signal Scoring Engine",
    kpi_extraction: "KPI Extraction (AI)",
  };

  const pipelineEndpoints: Record<string, string> = {
    "SEC Form 4 Filings": "sec-filings",
    "Market Data & Returns": "market-data",
    "Institutional 13F Holdings": "institutional",
    "Signal Scoring Engine": "signal-scoring",
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
          <Settings size={22} className="text-text-muted" />
          Platform Settings
        </h1>
        <p className="text-text-muted text-sm mt-1">
          Pipeline status, data sources, and configuration
        </p>
      </div>

      {/* Health */}
      <div className="bg-surface-1 border border-surface-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-text-primary">System Health</h2>
          <button
            onClick={fetchStatus}
            className="text-text-muted hover:text-text-primary transition-colors"
          >
            <RefreshCw size={14} />
          </button>
        </div>
        <div className="flex items-center gap-3">
          {health?.status === "ok" ? (
            <CheckCircle size={16} className="text-accent-green" />
          ) : (
            <AlertCircle size={16} className="text-accent-red" />
          )}
          <span className="text-sm text-text-secondary">
            API: <span className={health?.status === "ok" ? "text-accent-green" : "text-accent-red"}>
              {health?.status || "connecting..."}
            </span>
          </span>
        </div>
      </div>

      {/* Pipelines */}
      <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-surface-border">
          <h2 className="text-sm font-semibold text-text-primary">Data Pipeline Status</h2>
          <p className="text-xs text-text-muted mt-1">
            ETL pipelines that ingest and process financial data
          </p>
        </div>
        <div className="divide-y divide-surface-border">
          {loading ? (
            <div className="flex items-center justify-center h-32 text-text-muted text-sm">Loading...</div>
          ) : pipelines.length === 0 ? (
            <div className="px-5 py-8 text-center text-text-muted text-sm">
              No pipeline runs recorded yet
            </div>
          ) : (
            pipelines.map((p) => (
              <div key={p.pipeline} className="px-5 py-4 flex items-center gap-4">
                <div className="flex-1">
                  <div className="text-sm font-medium text-text-primary">
                    {pipelineLabels[p.pipeline] || p.pipeline}
                  </div>
                  <div className="text-xs text-text-muted mt-0.5">
                    {p.last_run
                      ? `Last run: ${new Date(p.last_run).toLocaleString()}`
                      : "Never run"}
                    {p.records_processed != null && ` · ${p.records_processed} records`}
                  </div>
                  {p.error && (
                    <div className="text-xs text-accent-red mt-1">{p.error}</div>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-mono ${
                      p.status === "success"
                        ? "bg-accent-green/15 text-accent-green"
                        : p.status === "running"
                        ? "bg-accent-blue/15 text-accent-blue"
                        : p.status === "failed"
                        ? "bg-accent-red/15 text-accent-red"
                        : "bg-surface-3 text-text-muted"
                    }`}
                  >
                    {p.status}
                  </span>
                  {pipelineEndpoints[pipelineLabels[p.pipeline]] && (
                    <button
                      onClick={() => triggerPipeline(pipelineEndpoints[pipelineLabels[p.pipeline]])}
                      className="text-xs text-accent-blue hover:underline"
                    >
                      Run
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Data Sources */}
      <div className="bg-surface-1 border border-surface-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Data Sources</h2>
        <div className="space-y-3 text-sm">
          {[
            { name: "SEC EDGAR", desc: "Form 3, 4, 5 insider transactions", url: "https://data.sec.gov", status: "active" },
            { name: "SEC EDGAR 13F", desc: "Institutional ownership filings", url: "https://data.sec.gov", status: "active" },
            { name: "Market Data (yfinance)", desc: "Historical prices for forward return calculations", url: "https://finance.yahoo.com", status: "active" },
            { name: "OpenAI GPT-4o", desc: "KPI extraction from earnings transcripts", url: "https://openai.com", status: "requires_key" },
          ].map((s) => (
            <div key={s.name} className="flex items-start gap-3 p-3 bg-surface-2 rounded-lg">
              <div
                className={`w-2 h-2 rounded-full mt-1 shrink-0 ${
                  s.status === "active" ? "bg-accent-green" : "bg-accent-amber"
                }`}
              />
              <div className="flex-1">
                <div className="font-medium text-text-primary">{s.name}</div>
                <div className="text-xs text-text-muted">{s.desc}</div>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded ${
                s.status === "active"
                  ? "bg-accent-green/15 text-accent-green"
                  : "bg-accent-amber/15 text-accent-amber"
              }`}>
                {s.status === "active" ? "Active" : "Key required"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
