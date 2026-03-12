"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getCompanies, getSectors, getLeaderboard, type Company, type CompositeScore } from "@/lib/api";
import { formatCurrency, SECTOR_COLORS, cn } from "@/lib/utils";
import { ScoreBadge } from "@/components/ui/ScoreBadge";
import { Search, Filter, TrendingUp } from "lucide-react";

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [scores, setScores] = useState<Map<number, CompositeScore>>(new Map());
  const [sectors, setSectors] = useState<string[]>([]);
  const [selectedSector, setSelectedSector] = useState<string>("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSectors().then(setSectors).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getCompanies({ sector: selectedSector || undefined, search: search || undefined, limit: 100 }),
      getLeaderboard(selectedSector || undefined),
    ])
      .then(([comps, scorelist]) => {
        setCompanies(comps);
        const map = new Map<number, CompositeScore>();
        scorelist.forEach((s) => map.set(s.company_id, s));
        setScores(map);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedSector, search]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">S&amp;P 500 Companies</h1>
          <p className="text-text-muted text-sm mt-1">
            {companies.length} companies · Ranked by composite opportunity score
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            placeholder="Search ticker or name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-surface-2 border border-surface-border rounded-lg pl-8 pr-4 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue w-56"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter size={13} className="text-text-muted" />
          <div className="flex gap-1 flex-wrap">
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
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Company Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-40 text-text-muted text-sm">
          <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mr-3" />
          Loading companies...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {companies.map((company) => {
            const score = scores.get(company.id);
            const sectorColor = SECTOR_COLORS[company.sector || ""] || "#3b82f6";

            return (
              <Link
                key={company.id}
                href={`/companies/${company.ticker}`}
                className="bg-surface-1 border border-surface-border rounded-xl p-4 hover:border-accent-blue/50 hover:bg-surface-2 transition-all card-hover"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2.5">
                    <div
                      className="w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold text-white"
                      style={{ backgroundColor: `${sectorColor}30`, border: `1px solid ${sectorColor}40`, color: sectorColor }}
                    >
                      {company.ticker.slice(0, 2)}
                    </div>
                    <div>
                      <div className="font-mono font-bold text-text-primary text-sm">{company.ticker}</div>
                      <div className="text-xs text-text-muted truncate max-w-32">{company.name}</div>
                    </div>
                  </div>
                  {score && <ScoreBadge score={score.composite_score} size="md" />}
                </div>

                <div className="flex items-center gap-2 mb-3">
                  <span
                    className="text-xs px-2 py-0.5 rounded-full font-medium"
                    style={{ backgroundColor: `${sectorColor}20`, color: sectorColor }}
                  >
                    {company.sector}
                  </span>
                  <span className="text-xs text-text-muted">{company.industry}</span>
                </div>

                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <div className="text-text-muted mb-0.5">Market Cap</div>
                    <div className="font-mono text-text-secondary">{formatCurrency(company.market_cap, true)}</div>
                  </div>
                  <div>
                    <div className="text-text-muted mb-0.5">Insider</div>
                    <div className={cn("font-mono", score?.insider_score && score.insider_score >= 7 ? "text-accent-green" : "text-text-secondary")}>
                      {score?.insider_score?.toFixed(1) || "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-text-muted mb-0.5">Momentum</div>
                    <div className={cn("font-mono", score?.business_momentum_score && score.business_momentum_score >= 7 ? "text-accent-cyan" : "text-text-secondary")}>
                      {score?.business_momentum_score?.toFixed(1) || "—"}
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
