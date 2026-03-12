"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getLeaderboard, getSectors, type CompositeScore } from "@/lib/api";
import { ScoreBadge, ScoreBar } from "@/components/ui/ScoreBadge";
import { formatCurrency, SECTOR_COLORS, cn } from "@/lib/utils";
import { TrendingUp, Filter, ArrowUpDown } from "lucide-react";

type SortKey = "composite_score" | "insider_score" | "institutional_score" | "business_momentum_score";

export default function LeaderboardPage() {
  const [scores, setScores] = useState<CompositeScore[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const [selectedSector, setSelectedSector] = useState<string>("");
  const [sortBy, setSortBy] = useState<SortKey>("composite_score");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSectors().then(setSectors).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    getLeaderboard(selectedSector || undefined, sortBy)
      .then(setScores)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedSector, sortBy]);

  const sortOptions: { key: SortKey; label: string }[] = [
    { key: "composite_score", label: "Composite" },
    { key: "insider_score", label: "Insider" },
    { key: "institutional_score", label: "Institutional" },
    { key: "business_momentum_score", label: "Momentum" },
  ];

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
          <TrendingUp size={22} className="text-accent-cyan" />
          Opportunity Score Leaderboard
        </h1>
        <p className="text-text-muted text-sm mt-1">
          Companies ranked by composite signal strength: insiders + institutions + momentum
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2">
          <ArrowUpDown size={13} className="text-text-muted" />
          <span className="text-xs text-text-muted">Sort by:</span>
          {sortOptions.map((opt) => (
            <button
              key={opt.key}
              onClick={() => setSortBy(opt.key)}
              className={cn(
                "px-3 py-1 rounded-lg text-xs font-medium transition-colors",
                sortBy === opt.key ? "bg-accent-blue text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Filter size={13} className="text-text-muted" />
          <button
            onClick={() => setSelectedSector("")}
            className={cn(
              "px-3 py-1 rounded-lg text-xs font-medium transition-colors",
              !selectedSector ? "bg-accent-blue text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
            )}
          >
            All
          </button>
          {sectors.map((s) => (
            <button
              key={s}
              onClick={() => setSelectedSector(s === selectedSector ? "" : s)}
              className={cn(
                "px-3 py-1 rounded-lg text-xs font-medium transition-colors",
                s === selectedSector ? "text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
              )}
              style={s === selectedSector ? { backgroundColor: SECTOR_COLORS[s] || "#3b82f6" } : {}}
            >
              {s.split(" ")[0]}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-text-muted text-sm">
            <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mr-3" />
            Loading leaderboard...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border bg-surface-2/50">
                  <th className="text-left py-3 px-4 text-xs text-text-muted font-medium">#</th>
                  <th className="text-left py-3 px-4 text-xs text-text-muted font-medium">Company</th>
                  <th className="text-left py-3 px-4 text-xs text-text-muted font-medium">Sector</th>
                  <th className="text-right py-3 px-4 text-xs text-text-muted font-medium">Composite</th>
                  <th className="text-right py-3 px-4 text-xs text-text-muted font-medium hidden md:table-cell">Insider</th>
                  <th className="text-right py-3 px-4 text-xs text-text-muted font-medium hidden md:table-cell">Institutional</th>
                  <th className="text-right py-3 px-4 text-xs text-text-muted font-medium hidden lg:table-cell">Momentum</th>
                  <th className="text-right py-3 px-4 text-xs text-text-muted font-medium hidden lg:table-cell">Buys 30d</th>
                  <th className="text-right py-3 px-4 text-xs text-text-muted font-medium hidden xl:table-cell">Mkt Cap</th>
                </tr>
              </thead>
              <tbody>
                {scores.map((s, i) => {
                  const sectorColor = SECTOR_COLORS[s.sector || ""] || "#3b82f6";
                  return (
                    <tr
                      key={s.company_id}
                      className={cn(
                        "border-b border-surface-border/50 hover:bg-surface-2/50 transition-colors",
                        i === 0 && "bg-accent-green/3"
                      )}
                    >
                      <td className="py-3 px-4 text-text-muted text-xs font-mono">{i + 1}</td>
                      <td className="py-3 px-4">
                        <Link href={`/companies/${s.ticker}`} className="flex items-center gap-2.5 hover:text-accent-blue transition-colors">
                          <div
                            className="w-7 h-7 rounded-md flex items-center justify-center text-xs font-bold shrink-0"
                            style={{ backgroundColor: `${sectorColor}20`, color: sectorColor }}
                          >
                            {s.ticker.slice(0, 2)}
                          </div>
                          <div>
                            <div className="font-mono font-semibold text-text-primary text-sm">{s.ticker}</div>
                            <div className="text-xs text-text-muted truncate max-w-36">{s.company_name}</div>
                          </div>
                        </Link>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className="text-xs px-2 py-0.5 rounded-full"
                          style={{ backgroundColor: `${sectorColor}20`, color: sectorColor }}
                        >
                          {s.sector?.split(" ")[0]}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <ScoreBadge score={s.composite_score} size="sm" />
                      </td>
                      <td className="py-3 px-4 text-right hidden md:table-cell">
                        <ScoreBadge score={s.insider_score} size="sm" />
                      </td>
                      <td className="py-3 px-4 text-right hidden md:table-cell">
                        <ScoreBadge score={s.institutional_score} size="sm" />
                      </td>
                      <td className="py-3 px-4 text-right hidden lg:table-cell">
                        <ScoreBadge score={s.business_momentum_score} size="sm" />
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-text-secondary text-xs hidden lg:table-cell">
                        {s.buys_30d || 0}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-text-muted text-xs hidden xl:table-cell">
                        {formatCurrency(s.market_cap, true)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Score explanation */}
      <div className="bg-surface-1 border border-surface-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-3">Composite Score Methodology</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-text-muted">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-accent-blue" />
              <strong className="text-text-secondary">Insider Conviction (30%)</strong>
              — Weighted average signal score of recent insider purchases, adjusted for buy/sell ratio
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-accent-green" />
              <strong className="text-text-secondary">Institutional Accumulation (25%)</strong>
              — Ratio of institutional buyers to sellers from latest 13F filings
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-accent-cyan" />
              <strong className="text-text-secondary">Business Momentum (25%)</strong>
              — Average YoY growth across financial and operational KPIs
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-accent-amber" />
              <strong className="text-text-secondary">Industry Expansion (20%)</strong>
              — Sector-wide buildout and growth metrics
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
