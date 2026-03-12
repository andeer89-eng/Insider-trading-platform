"use client";
import { useEffect, useState } from "react";
import { getTopSignals, getSectorHeatmap, getClusterEvents, type TopSignal, type SectorHeatmap, type ClusterEvent } from "@/lib/api";
import { SignalTable } from "@/components/ui/SignalTable";
import { SectorHeatmapChart } from "@/components/charts/SectorHeatmap";
import { ScoreBadge } from "@/components/ui/ScoreBadge";
import { StatCard } from "@/components/ui/StatCard";
import { formatCurrency, formatDate, cn } from "@/lib/utils";
import { Zap, Filter, AlertTriangle, TrendingUp } from "lucide-react";
import Link from "next/link";

export default function SignalsPage() {
  const [signals, setSignals] = useState<TopSignal[]>([]);
  const [sectors, setSectors] = useState<SectorHeatmap[]>([]);
  const [clusters, setClusters] = useState<ClusterEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const [days, setDays] = useState(30);
  const [minScore, setMinScore] = useState(5);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getTopSignals(days, minScore, 100),
      getSectorHeatmap(days),
      getClusterEvents(90),
    ])
      .then(([sigs, sects, clusts]) => {
        setSignals(sigs);
        setSectors(sects);
        setClusters(clusts);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [days, minScore]);

  const buyCount = signals.filter(s => s.transaction_type?.toLowerCase().includes("buy")).length;
  const totalBuyValue = signals.reduce((sum, s) => sum + (s.transaction_value || 0), 0);
  const clusterCount = signals.filter(s => s.cluster_flag).length;
  const avgScore = signals.length > 0
    ? signals.reduce((sum, s) => sum + (s.signal_score || 0), 0) / signals.length
    : 0;

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
            <Zap size={22} className="text-accent-green" />
            Insider Signal Engine
          </h1>
          <p className="text-text-muted text-sm mt-1">
            High-conviction insider purchases scored 0–10 across S&amp;P 500
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-surface-1 border border-surface-border rounded-xl p-4 flex flex-wrap gap-4 items-center">
        <div className="flex items-center gap-2">
          <Filter size={13} className="text-text-muted" />
          <span className="text-xs text-text-muted font-medium">Lookback:</span>
          {[7, 14, 30, 60, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={cn(
                "px-3 py-1 rounded-lg text-xs font-medium transition-colors",
                days === d ? "bg-accent-blue text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
              )}
            >
              {d}d
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted font-medium">Min Score:</span>
          {[0, 4, 5, 6, 7, 8].map((s) => (
            <button
              key={s}
              onClick={() => setMinScore(s)}
              className={cn(
                "px-3 py-1 rounded-lg text-xs font-medium transition-colors",
                minScore === s ? "bg-accent-green text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
              )}
            >
              {s}+
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Signals Found" value={signals.length} accent="blue" />
        <StatCard label="Total Buy Value" value={formatCurrency(totalBuyValue, true)} accent="green" />
        <StatCard label="Cluster Events" value={clusterCount} sub="Multiple insiders" accent="amber" />
        <StatCard label="Avg Signal Score" value={avgScore.toFixed(1)} accent="cyan" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Main signals table */}
        <div className="xl:col-span-2">
          <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-surface-border flex items-center justify-between">
              <span className="text-sm font-semibold text-text-primary">
                Top Signals ({signals.length})
              </span>
              <span className="text-xs text-text-muted">{days}d lookback · min score {minScore}</span>
            </div>
            {loading ? (
              <div className="flex items-center justify-center h-40 text-text-muted text-sm">
                <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mr-3" />
                Loading signals...
              </div>
            ) : (
              <SignalTable signals={signals} />
            )}
          </div>
        </div>

        {/* Right: Clusters + Sector Heatmap */}
        <div className="space-y-5">
          {/* Cluster events */}
          <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-surface-border flex items-center gap-2">
              <AlertTriangle size={14} className="text-accent-amber" />
              <span className="text-sm font-semibold text-text-primary">Cluster Buying</span>
            </div>
            <div className="divide-y divide-surface-border/50">
              {clusters.slice(0, 8).map((evt) => (
                <div key={evt.id} className="px-4 py-3 flex items-center gap-3 hover:bg-surface-2/50 transition-colors">
                  <ScoreBadge score={evt.cluster_score} size="sm" />
                  <div className="flex-1 min-w-0">
                    <Link href={`/companies/${evt.ticker}`} className="text-sm font-mono font-semibold text-text-primary hover:text-accent-blue">
                      {evt.ticker}
                    </Link>
                    <div className="text-xs text-text-muted truncate">{evt.company_name}</div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-xs text-accent-amber font-semibold">{evt.insider_count} insiders</div>
                    <div className="text-xs text-text-muted font-mono">{formatCurrency(evt.total_value, true)}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Sector heatmap */}
          <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-surface-border">
              <span className="text-sm font-semibold text-text-primary">Sector Sentiment</span>
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
