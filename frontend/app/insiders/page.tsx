"use client";
import { useEffect, useState } from "react";
import { getTransactions, type InsiderTransaction } from "@/lib/api";
import { SignalTable } from "@/components/ui/SignalTable";
import { StatCard } from "@/components/ui/StatCard";
import { formatCurrency, cn } from "@/lib/utils";
import { Users, Filter, Download } from "lucide-react";

export default function InsidersPage() {
  const [transactions, setTransactions] = useState<InsiderTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [txType, setTxType] = useState<string>("");
  const [minValue, setMinValue] = useState<number>(0);

  useEffect(() => {
    setLoading(true);
    getTransactions({
      days,
      transaction_type: txType || undefined,
      min_value: minValue > 0 ? minValue : undefined,
      limit: 200,
    })
      .then(setTransactions)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [days, txType, minValue]);

  const buys = transactions.filter((t) => t.transaction_type?.toLowerCase().includes("buy"));
  const sells = transactions.filter((t) => t.transaction_type?.toLowerCase().includes("sell"));
  const buyValue = buys.reduce((s, t) => s + (t.transaction_value || 0), 0);
  const sellValue = sells.reduce((s, t) => s + (t.transaction_value || 0), 0);

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
          <Users size={22} className="text-accent-blue" />
          Insider Trading Activity
        </h1>
        <p className="text-text-muted text-sm mt-1">
          All Form 3, 4, 5 transactions from SEC EDGAR
        </p>
      </div>

      {/* Filters */}
      <div className="bg-surface-1 border border-surface-border rounded-xl p-4 flex flex-wrap gap-4 items-center">
        <div className="flex items-center gap-2">
          <Filter size={13} className="text-text-muted" />
          <span className="text-xs text-text-muted">Lookback:</span>
          {[7, 14, 30, 60, 90, 180, 365].map((d) => (
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
          <span className="text-xs text-text-muted">Type:</span>
          {["", "Buy", "Sell", "Award"].map((t) => (
            <button
              key={t}
              onClick={() => setTxType(t)}
              className={cn(
                "px-3 py-1 rounded-lg text-xs font-medium transition-colors",
                txType === t ? "bg-accent-blue text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
              )}
            >
              {t || "All"}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">Min Value:</span>
          {[0, 100_000, 500_000, 1_000_000, 5_000_000].map((v) => (
            <button
              key={v}
              onClick={() => setMinValue(v)}
              className={cn(
                "px-3 py-1 rounded-lg text-xs font-medium transition-colors",
                minValue === v ? "bg-accent-blue text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
              )}
            >
              {v === 0 ? "Any" : formatCurrency(v, true)}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Total Transactions" value={transactions.length} accent="blue" />
        <StatCard label="Buy Transactions" value={buys.length} accent="green" />
        <StatCard label="Total Buy Value" value={formatCurrency(buyValue, true)} accent="cyan" />
        <StatCard label="Buy/Sell Ratio" value={sells.length > 0 ? (buys.length / sells.length).toFixed(2) : "∞"} accent="amber" />
      </div>

      {/* Table */}
      <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-surface-border flex items-center justify-between">
          <span className="text-sm font-semibold text-text-primary">
            Transactions ({transactions.length})
          </span>
          <span className="text-xs text-text-muted">{days}d lookback</span>
        </div>
        {loading ? (
          <div className="flex items-center justify-center h-40 text-text-muted text-sm">
            <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mr-3" />
            Loading transactions...
          </div>
        ) : (
          <SignalTable signals={transactions as unknown as Parameters<typeof SignalTable>[0]["signals"]} />
        )}
      </div>
    </div>
  );
}
