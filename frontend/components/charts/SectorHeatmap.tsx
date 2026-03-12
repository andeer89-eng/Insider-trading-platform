"use client";
import { SECTOR_COLORS, formatCurrency, cn } from "@/lib/utils";
import type { SectorHeatmap } from "@/lib/api";

interface SectorHeatmapProps {
  data: SectorHeatmap[];
}

export function SectorHeatmapChart({ data }: SectorHeatmapProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-text-muted text-sm">
        No sector data
      </div>
    );
  }

  const maxBuyValue = Math.max(...data.map((d) => d.total_buy_value || 0));

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
      {data.map((sector) => {
        const buyRatio = (sector.buys || 0) / ((sector.total_trades || 1));
        const intensity = maxBuyValue > 0 ? (sector.total_buy_value || 0) / maxBuyValue : 0;
        const color = SECTOR_COLORS[sector.sector] || "#3b82f6";
        const netBullish = buyRatio > 0.5;

        return (
          <div
            key={sector.sector}
            className="rounded-lg border border-surface-border p-3 bg-surface-2 hover:border-opacity-70 transition-all"
            style={{ borderColor: `${color}30` }}
          >
            <div className="flex items-start justify-between mb-2">
              <div
                className="text-xs font-semibold truncate"
                style={{ color }}
              >
                {sector.sector}
              </div>
              <div
                className={cn(
                  "text-xs font-mono px-1.5 py-0.5 rounded",
                  netBullish
                    ? "bg-accent-green/15 text-accent-green"
                    : "bg-accent-red/15 text-accent-red"
                )}
              >
                {sector.avg_signal_score?.toFixed(1) || "—"}
              </div>
            </div>

            {/* Buy/sell bar */}
            <div className="h-1.5 bg-surface-border rounded-full overflow-hidden mb-2">
              <div
                className="h-full rounded-full bg-gradient-to-r from-accent-green to-accent-cyan"
                style={{ width: `${buyRatio * 100}%` }}
              />
            </div>

            <div className="grid grid-cols-2 gap-1 text-xs font-mono">
              <div>
                <span className="text-text-muted">Buys </span>
                <span className="text-accent-green">{sector.buys || 0}</span>
              </div>
              <div>
                <span className="text-text-muted">Sells </span>
                <span className="text-accent-red">{sector.sells || 0}</span>
              </div>
            </div>

            <div className="mt-1.5 text-xs text-text-muted">
              Vol: <span className="text-text-secondary font-mono">
                {formatCurrency(sector.total_buy_value, true)}
              </span>
            </div>

            {/* Intensity bar */}
            <div className="mt-2 h-0.5 bg-surface-border rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{ width: `${intensity * 100}%`, backgroundColor: color, opacity: 0.7 }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
