"use client";
import { Search, Bell, RefreshCw } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { formatDate } from "@/lib/utils";

export function Topbar() {
  const [query, setQuery] = useState("");
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/companies/${query.trim().toUpperCase()}`);
    }
  };

  return (
    <header className="h-14 bg-surface-1 border-b border-surface-border flex items-center px-6 gap-4 shrink-0">
      {/* Search */}
      <form onSubmit={handleSearch} className="flex-1 max-w-md">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder="Search ticker (e.g. NVDA, TSLA)..."
            value={query}
            onChange={(e) => setQuery(e.target.value.toUpperCase())}
            className="w-full bg-surface-2 border border-surface-border rounded-lg pl-9 pr-4 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue transition-colors"
          />
        </div>
      </form>

      {/* Right side */}
      <div className="flex items-center gap-4 ml-auto">
        <div className="text-xs text-text-muted font-mono">
          {formatDate(new Date().toISOString().split("T")[0])}
        </div>

        <button className="text-text-muted hover:text-text-primary transition-colors">
          <RefreshCw size={15} />
        </button>

        <button className="relative text-text-muted hover:text-text-primary transition-colors">
          <Bell size={15} />
          <span className="absolute -top-1 -right-1 w-2 h-2 bg-accent-blue rounded-full" />
        </button>

        <div className="flex items-center gap-2 bg-surface-2 border border-surface-border rounded-lg px-3 py-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
          <span className="text-xs text-text-secondary font-mono">Live</span>
        </div>
      </div>
    </header>
  );
}
