"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  TrendingUp,
  Building2,
  BarChart3,
  GitCompare,
  Factory,
  Users,
  Activity,
  Settings,
  Zap,
} from "lucide-react";

const nav = [
  {
    group: "Overview",
    items: [
      { href: "/", label: "Dashboard", icon: LayoutDashboard },
      { href: "/signals", label: "Insider Signals", icon: Zap },
    ],
  },
  {
    group: "Research",
    items: [
      { href: "/companies", label: "Companies", icon: Building2 },
      { href: "/insiders", label: "Insider Trades", icon: Users },
      { href: "/institutional", label: "Institutional", icon: BarChart3 },
    ],
  },
  {
    group: "Analytics",
    items: [
      { href: "/metrics", label: "KPI Metrics", icon: Activity },
      { href: "/compare", label: "Metric Compare", icon: GitCompare },
      { href: "/industry", label: "Industry Buildout", icon: Factory },
    ],
  },
  {
    group: "Platform",
    items: [
      { href: "/leaderboard", label: "Leaderboard", icon: TrendingUp },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 bg-surface-1 border-r border-surface-border flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-5 py-4 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-accent-blue rounded-md flex items-center justify-center text-xs font-bold text-white">
            FT
          </div>
          <div>
            <div className="text-sm font-bold text-text-primary tracking-wide">FINTEL</div>
            <div className="text-xs text-text-muted">Intelligence Platform</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-3">
        {nav.map((group) => (
          <div key={group.group} className="mb-5">
            <div className="px-2 py-1 text-xs font-semibold text-text-muted uppercase tracking-widest mb-1">
              {group.group}
            </div>
            {group.items.map(({ href, label, icon: Icon }) => {
              const active = pathname === href || (href !== "/" && pathname.startsWith(href));
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors mb-0.5",
                    active
                      ? "bg-accent-blue/15 text-accent-blue border border-accent-blue/20"
                      : "text-text-secondary hover:text-text-primary hover:bg-surface-3"
                  )}
                >
                  <Icon size={15} className="shrink-0" />
                  {label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-surface-border">
        <div className="text-xs text-text-muted">
          <div className="flex items-center gap-1.5 mb-1">
            <div className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
            <span>Live data</span>
          </div>
          <div>S&amp;P 500 · SEC EDGAR</div>
        </div>
      </div>
    </aside>
  );
}
