import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  className?: string;
  accent?: "blue" | "green" | "red" | "amber" | "purple" | "cyan";
}

const accentMap = {
  blue: "border-accent-blue/20 bg-accent-blue/5",
  green: "border-accent-green/20 bg-accent-green/5",
  red: "border-accent-red/20 bg-accent-red/5",
  amber: "border-accent-amber/20 bg-accent-amber/5",
  purple: "border-accent-purple/20 bg-accent-purple/5",
  cyan: "border-accent-cyan/20 bg-accent-cyan/5",
};

const accentText = {
  blue: "text-accent-blue",
  green: "text-accent-green",
  red: "text-accent-red",
  amber: "text-accent-amber",
  purple: "text-accent-purple",
  cyan: "text-accent-cyan",
};

export function StatCard({
  label,
  value,
  sub,
  trend,
  trendValue,
  className,
  accent = "blue",
}: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border p-4 bg-surface-2",
        accentMap[accent],
        className
      )}
    >
      <div className="text-xs text-text-muted uppercase tracking-wider mb-2 font-medium">
        {label}
      </div>
      <div className={cn("text-2xl font-bold font-mono", accentText[accent])}>
        {value}
      </div>
      {(sub || trendValue) && (
        <div className="flex items-center gap-2 mt-1">
          {sub && <div className="text-xs text-text-muted">{sub}</div>}
          {trendValue && (
            <div
              className={cn(
                "text-xs font-mono",
                trend === "up" && "text-accent-green",
                trend === "down" && "text-accent-red",
                trend === "neutral" && "text-text-muted"
              )}
            >
              {trendValue}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
