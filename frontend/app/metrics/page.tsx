"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getMetrics, getMetricCategories, type MetricDef } from "@/lib/api";
import { Activity, Filter, Search } from "lucide-react";
import { cn } from "@/lib/utils";

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<MetricDef[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getMetrics(), getMetricCategories()])
      .then(([m, c]) => { setMetrics(m); setCategories(c); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filtered = metrics.filter((m) => {
    const matchCat = !selectedCategory || m.category === selectedCategory;
    const matchSearch = !search ||
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      (m.display_name || "").toLowerCase().includes(search.toLowerCase());
    return matchCat && matchSearch;
  });

  const grouped: Record<string, MetricDef[]> = {};
  filtered.forEach((m) => {
    if (!grouped[m.category]) grouped[m.category] = [];
    grouped[m.category].push(m);
  });

  const categoryColors: Record<string, string> = {
    financial: "#22c55e",
    infrastructure: "#3b82f6",
    production: "#f59e0b",
    product: "#a855f7",
    operational: "#06b6d4",
    esg: "#84cc16",
  };

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
          <Activity size={22} className="text-accent-purple" />
          KPI Metrics Registry
        </h1>
        <p className="text-text-muted text-sm mt-1">
          {metrics.length} operational metrics tracked across S&amp;P 500 companies
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            placeholder="Search metrics..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-surface-2 border border-surface-border rounded-lg pl-8 pr-4 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue w-56"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Filter size={13} className="text-text-muted" />
          <button
            onClick={() => setSelectedCategory("")}
            className={cn(
              "px-3 py-1 rounded-lg text-xs font-medium transition-colors",
              !selectedCategory ? "bg-accent-blue text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
            )}
          >
            All
          </button>
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => setSelectedCategory(c === selectedCategory ? "" : c)}
              className={cn(
                "px-3 py-1 rounded-lg text-xs font-medium transition-colors capitalize",
                c === selectedCategory ? "text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
              )}
              style={c === selectedCategory ? { backgroundColor: categoryColors[c] || "#3b82f6" } : {}}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Metrics grid by category */}
      {loading ? (
        <div className="flex items-center justify-center h-40 text-text-muted text-sm">
          <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mr-3" />
          Loading metrics...
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped).map(([category, mets]) => {
            const color = categoryColors[category] || "#3b82f6";
            return (
              <div key={category}>
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                  <h2 className="text-sm font-semibold text-text-primary capitalize">{category}</h2>
                  <span className="text-xs text-text-muted">({mets.length})</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
                  {mets.map((m) => (
                    <div
                      key={m.id}
                      className="bg-surface-1 border border-surface-border rounded-lg p-3 hover:border-opacity-70 transition-all"
                      style={{ borderColor: `${color}25` }}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-text-primary truncate">
                            {m.display_name || m.name}
                          </div>
                          <code className="text-xs text-text-muted font-mono">{m.name}</code>
                        </div>
                        <div className="shrink-0 flex gap-1">
                          {m.unit && (
                            <span
                              className="text-xs px-1.5 py-0.5 rounded font-mono"
                              style={{ backgroundColor: `${color}15`, color }}
                            >
                              {m.unit}
                            </span>
                          )}
                        </div>
                      </div>
                      {m.description && (
                        <p className="text-xs text-text-muted mt-1.5 line-clamp-2">{m.description}</p>
                      )}
                      <div className="flex items-center gap-2 mt-2 text-xs text-text-muted">
                        <span>{m.frequency}</span>
                        <span>·</span>
                        <span>{m.source || "—"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
