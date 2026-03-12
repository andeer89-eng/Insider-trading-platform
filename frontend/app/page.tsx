"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getDashboard, getSectorHeatmap,
  type DashboardData, type SectorHeatmap,
} from "@/lib/api";
import { StatCard } from "@/components/ui/StatCard";
import { SignalTable } from "@/components/ui/SignalTable";
import { ScoreBadge, ScoreBar } from "@/components/ui/ScoreBadge";
import { SectorHeatmapChart } from "@/components/charts/SectorHeatmap";
import { formatCurrency, formatDate, cn } from "@/lib/utils";
import {
  Zap, TrendingUp, Users, AlertTriangle,
  ArrowRight, Activity, Building2,
} from "lucide-react";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [sectors, setSectors] = useState<SectorHeatmap[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getDashboard(), getSectorHeatmap(30)])
      .then(([dash, sect]) => {
        setData(dash);
        setSectors(sect);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-3 text-text-muted">
          <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
          Loading intelligence data...
        </div>
      </div>
    );
  }

  const topSignals = data?.top_signals || [];
  const topScores = data?.top_composite_scores || [];
  const clusters = data?.recent_cluster_events || [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">
            Financial Intelligence Dashboard
          </h1>
          <p className="text-text-muted text-sm mt-1">
            {formatDate(data?.market_date || new Date().toISOString())} · S&amp;P 500 · Real-time insider intelligence
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-text-muted bg-surface-2 border border-surface-border px-3 py-1.5 rounded-lg">
          <div className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
          Live data feed
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Top Signal Score Today"
          value={topSignals[0]?.signal_score?.toFixed(1) || "—"}
          sub={topSignals[0]?.ticker}
          accent="green"
        />
        <StatCard
          label="Insider Buy Value (30d)"
          value={formatCurrency(data?.total_buy_value_today || 0, true)}
          sub="Open-market purchases"
          accent="blue"
        />
        <StatCard
          label="Active Cluster Events"
          value={clusters.length}
          sub="Multiple insiders buying"
          accent="amber"
        />
        <StatCard
          label="Transactions Today"
          value={data?.total_transactions_today || 0}
          sub="Form 4 filings"
          accent="purple"
        />
      </div>

      {/* Main content: 2 columns */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left: Top insider signals */}
        <div className="xl:col-span-2 space-y-6">
          {/* Top Signals */}
          <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-surface-border">
              <div className="flex items-center gap-2">
                <Zap size={16} className="text-accent-green" />
                <h2 className="text-sm font-semibold text-text-primary">Top Insider Signals Today</h2>
              </div>
              <Link
                href="/signals"
                className="text-xs text-accent-blue hover:underline flex items-center gap-1"
              >
                View all <ArrowRight size={12} />
              </Link>
            </div>
            <SignalTable signals={topSignals.slice(0, 15)} compact />
          </div>

          {/* Cluster Events */}
          <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
            <div className="flex items-center gap-2 px-5 py-4 border-b border-surface-border">
              <AlertTriangle size={16} className="text-accent-amber" />
              <h2 className="text-sm font-semibold text-text-primary">Recent Cluster Buying Events</h2>
              <span className="text-xs text-text-muted">(multiple insiders)</span>
            </div>
            <div className="divide-y divide-surface-border/50">
              {clusters.length === 0 ? (
                <div className="px-5 py-8 text-center text-text-muted text-sm">No cluster events in range</div>
              ) : (
                clusters.slice(0, 8).map((evt) => (
                  <div key={evt.id} className="px-5 py-3 flex items-center gap-4 hover:bg-surface-2/50 transition-colors">
                    <div className="shrink-0">
                      <ScoreBadge score={evt.cluster_score} size="md" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <Link href={`/companies/${evt.ticker}`} className="font-mono font-semibold text-text-primary hover:text-accent-blue text-sm">
                        {evt.ticker}
                      </Link>
                      <div className="text-xs text-text-muted truncate">{evt.company_name}</div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-xs font-semibold text-accent-amber">
                        {evt.insider_count} insiders
                      </div>
                      <div className="text-xs text-text-muted font-mono">
                        {formatCurrency(evt.total_value, true)}
                      </div>
                    </div>
                    <div className="text-xs text-text-muted font-mono shrink-0 hidden lg:block">
                      {formatDate(evt.end_date)}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Composite Leaderboard */}
          <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-surface-border">
              <div className="flex items-center gap-2">
                <TrendingUp size={16} className="text-accent-cyan" />
                <h2 className="text-sm font-semibold text-text-primary">Top Opportunity Scores</h2>
              </div>
              <Link href="/leaderboard" className="text-xs text-accent-blue hover:underline flex items-center gap-1">
                Full list <ArrowRight size={12} />
              </Link>
            </div>
            <div className="divide-y divide-surface-border/50">
              {topScores.slice(0, 10).map((s, i) => (
                <div key={s.company_id} className="px-5 py-3 hover:bg-surface-2/50 transition-colors">
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-text-muted font-mono w-4 shrink-0">{i + 1}</span>
                    <Link
                      href={`/companies/${s.ticker}`}
                      className="font-mono font-semibold text-text-primary hover:text-accent-blue text-sm flex-1 min-w-0"
                    >
                      {s.ticker}
                      <span className="text-text-muted font-normal font-sans text-xs ml-1.5 truncate hidden md:inline">
                        {s.company_name}
                      </span>
                    </Link>
                    <ScoreBadge score={s.composite_score} size="sm" />
                  </div>
                  <div className="mt-1.5 pl-7 space-y-1">
                    <ScoreBar score={s.insider_score} label="Insider" />
                    <ScoreBar score={s.institutional_score} label="Institutional" />
                    <ScoreBar score={s.business_momentum_score} label="Momentum" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Sector Sentiment */}
          <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
            <div className="flex items-center gap-2 px-5 py-4 border-b border-surface-border">
              <Activity size={16} className="text-accent-purple" />
              <h2 className="text-sm font-semibold text-text-primary">Sector Insider Sentiment</h2>
            </div>
            <div className="p-4">
              <SectorHeatmapChart data={sectors} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
