"use client";
import Link from "next/link";
import { cn, formatCurrency, formatDate, txTypeColor, formatNumber } from "@/lib/utils";
import { ScoreBadge } from "./ScoreBadge";
import type { TopSignal } from "@/lib/api";
import { AlertTriangle, ExternalLink } from "lucide-react";

interface SignalTableProps {
  signals: TopSignal[];
  showCompany?: boolean;
  compact?: boolean;
}

export function SignalTable({ signals, showCompany = true, compact = false }: SignalTableProps) {
  if (!signals.length) {
    return (
      <div className="flex items-center justify-center h-32 text-text-muted text-sm">
        No signals found
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-surface-border">
            <th className="text-left py-2.5 px-3 text-xs text-text-muted font-medium uppercase tracking-wider">Score</th>
            {showCompany && (
              <th className="text-left py-2.5 px-3 text-xs text-text-muted font-medium uppercase tracking-wider">Company</th>
            )}
            <th className="text-left py-2.5 px-3 text-xs text-text-muted font-medium uppercase tracking-wider">Insider</th>
            <th className="text-left py-2.5 px-3 text-xs text-text-muted font-medium uppercase tracking-wider">Type</th>
            {!compact && (
              <>
                <th className="text-right py-2.5 px-3 text-xs text-text-muted font-medium uppercase tracking-wider">Shares</th>
                <th className="text-right py-2.5 px-3 text-xs text-text-muted font-medium uppercase tracking-wider">Price</th>
              </>
            )}
            <th className="text-right py-2.5 px-3 text-xs text-text-muted font-medium uppercase tracking-wider">Value</th>
            <th className="text-right py-2.5 px-3 text-xs text-text-muted font-medium uppercase tracking-wider">Δ Own%</th>
            <th className="text-right py-2.5 px-3 text-xs text-text-muted font-medium uppercase tracking-wider">Date</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((s) => (
            <tr
              key={s.id || s.transaction_id}
              className="border-b border-surface-border/50 hover:bg-surface-2/50 transition-colors group"
            >
              <td className="py-2.5 px-3">
                <div className="flex items-center gap-1.5">
                  <ScoreBadge score={s.signal_score} size="sm" />
                  {s.cluster_flag && (
                    <span title="Cluster buying" className="text-accent-amber">
                      <AlertTriangle size={11} />
                    </span>
                  )}
                </div>
              </td>
              {showCompany && (
                <td className="py-2.5 px-3">
                  <Link
                    href={`/companies/${s.ticker}`}
                    className="flex items-center gap-1.5 hover:text-accent-blue transition-colors"
                  >
                    <span className="font-mono font-semibold text-text-primary">{s.ticker}</span>
                    <span className="text-text-muted text-xs truncate max-w-28 hidden md:block">
                      {s.company_name}
                    </span>
                  </Link>
                </td>
              )}
              <td className="py-2.5 px-3">
                <div className="text-text-secondary text-xs">{s.insider_name || "—"}</div>
                <div className="text-text-muted text-xs">{s.insider_role}</div>
              </td>
              <td className="py-2.5 px-3">
                <span className={cn("font-medium text-xs", txTypeColor(s.transaction_type))}>
                  {s.transaction_type}
                </span>
              </td>
              {!compact && (
                <>
                  <td className="py-2.5 px-3 text-right font-mono text-text-secondary text-xs">
                    {formatNumber(s.shares)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-text-secondary text-xs">
                    {s.price ? `$${s.price.toFixed(2)}` : "—"}
                  </td>
                </>
              )}
              <td className="py-2.5 px-3 text-right font-mono font-medium text-text-primary text-xs">
                {formatCurrency(s.transaction_value, true)}
              </td>
              <td className="py-2.5 px-3 text-right font-mono text-xs">
                {s.ownership_change_pct != null ? (
                  <span className={s.ownership_change_pct > 0 ? "text-accent-green" : "text-accent-red"}>
                    {s.ownership_change_pct > 0 ? "+" : ""}
                    {Number(s.ownership_change_pct).toFixed(1)}%
                  </span>
                ) : "—"}
              </td>
              <td className="py-2.5 px-3 text-right text-text-muted text-xs font-mono">
                {formatDate(s.transaction_date)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
