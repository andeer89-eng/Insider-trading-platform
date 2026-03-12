"use client";
import { useEffect, useState } from "react";
import { getNetAccumulation, getSectors } from "@/lib/api";
import { StatCard } from "@/components/ui/StatCard";
import { ScoreBadge } from "@/components/ui/ScoreBadge";
import { formatCurrency, formatNumber, SECTOR_COLORS, cn } from "@/lib/utils";
import { BarChart3, Filter, TrendingUp, TrendingDown } from "lucide-react";
import Link from "next/link";

interface AccumulationRow {
  ticker: string;
  company_name: string;
  sector: string;
  quarter: string;
  net_change: number;
  num_buyers: number;
  num_sellers: number;
  shares_bought: number;
  shares_sold: number;
  accum_score: number;
}

export default function InstitutionalPage() {
  const [data, setData] = useState<AccumulationRow[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const [selectedSector, setSelectedSector] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"accumulation" | "distribution">("accumulation");

  useEffect(() => {
    getSectors().then(setSectors).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    getNetAccumulation(selectedSector || undefined)
      .then((rows) => setData(rows as AccumulationRow[]))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedSector]);

  const sorted = [...data].sort((a, b) =>
    viewMode === "accumulation"
      ? (b.net_change || 0) - (a.net_change || 0)
      : (a.net_change || 0) - (b.net_change || 0)
  ).slice(0, 50);

  const totalBuyers = data.reduce((s, r) => s + (r.num_buyers || 0), 0);
  const totalSellers = data.reduce((s, r) => s + (r.num_sellers || 0), 0);
  const netAccum = data.filter((r) => (r.net_change || 0) > 0).length;

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
          <BarChart3 size={22} className="text-accent-amber" />
          Institutional Ownership
        </h1>
        <p className="text-text-muted text-sm mt-1">
          13F filing analysis: net accumulation and distribution by major asset managers
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Total Institutional Buyers" value={totalBuyers} accent="green" />
        <StatCard label="Total Institutional Sellers" value={totalSellers} accent="red" />
        <StatCard label="Companies w/ Net Accum." value={netAccum} accent="blue" />
        <StatCard label="Buy/Sell Ratio" value={totalSellers > 0 ? (totalBuyers / totalSellers).toFixed(2) : "∞"} accent="amber" />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode("accumulation")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
              viewMode === "accumulation" ? "bg-accent-green text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
            )}
          >
            <TrendingUp size={12} /> Accumulation
          </button>
          <button
            onClick={() => setViewMode("distribution")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
              viewMode === "distribution" ? "bg-accent-red text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
            )}
          >
            <TrendingDown size={12} /> Distribution
          </button>
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
            All Sectors
          </button>
          {sectors.slice(0, 5).map((s) => (
            <button
              key={s}
              onClick={() => setSelectedSector(s === selectedSector ? "" : s)}
              className={cn(
                "px-3 py-1 rounded-lg text-xs font-medium transition-colors",
                s === selectedSector ? "text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
              )}
              style={s === selectedSector ? { backgroundColor: SECTOR_COLORS[s] } : {}}
            >
              {s.split(" ")[0]}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-surface-border">
          <span className="text-sm font-semibold text-text-primary">
            Net Institutional {viewMode === "accumulation" ? "Accumulation" : "Distribution"} — Last Quarter
          </span>
        </div>
        {loading ? (
          <div className="flex items-center justify-center h-40 text-text-muted text-sm">
            <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mr-3" />
            Loading institutional data...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border bg-surface-2/50">
                  <th className="text-left py-2.5 px-4 text-xs text-text-muted">Company</th>
                  <th className="text-left py-2.5 px-4 text-xs text-text-muted hidden md:table-cell">Sector</th>
                  <th className="text-right py-2.5 px-4 text-xs text-text-muted">Net Change</th>
                  <th className="text-right py-2.5 px-4 text-xs text-text-muted hidden md:table-cell">Buyers</th>
                  <th className="text-right py-2.5 px-4 text-xs text-text-muted hidden md:table-cell">Sellers</th>
                  <th className="text-right py-2.5 px-4 text-xs text-text-muted hidden lg:table-cell">Shares Bought</th>
                  <th className="text-right py-2.5 px-4 text-xs text-text-muted">Score</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((row) => {
                  const netPositive = (row.net_change || 0) > 0;
                  const sectorColor = SECTOR_COLORS[row.sector] || "#3b82f6";
                  return (
                    <tr key={row.ticker} className="border-b border-surface-border/50 hover:bg-surface-2/50 transition-colors">
                      <td className="py-2.5 px-4">
                        <Link href={`/companies/${row.ticker}`} className="flex items-center gap-2 hover:text-accent-blue transition-colors">
                          <div
                            className="w-6 h-6 rounded shrink-0 flex items-center justify-center text-xs font-bold"
                            style={{ backgroundColor: `${sectorColor}20`, color: sectorColor }}
                          >
                            {row.ticker.slice(0, 2)}
                          </div>
                          <div>
                            <div className="font-mono font-semibold text-text-primary text-xs">{row.ticker}</div>
                            <div className="text-xs text-text-muted truncate max-w-28">{row.company_name}</div>
                          </div>
                        </Link>
                      </td>
                      <td className="py-2.5 px-4 hidden md:table-cell">
                        <span className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: `${sectorColor}15`, color: sectorColor }}>
                          {row.sector?.split(" ")[0]}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono text-sm">
                        <span className={netPositive ? "text-accent-green" : "text-accent-red"}>
                          {netPositive ? "+" : ""}{formatNumber(row.net_change)}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono text-xs text-accent-green hidden md:table-cell">
                        {row.num_buyers || 0}
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono text-xs text-accent-red hidden md:table-cell">
                        {row.num_sellers || 0}
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono text-xs text-text-secondary hidden lg:table-cell">
                        {formatNumber(row.shares_bought)}
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        <ScoreBadge score={row.accum_score} size="sm" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
