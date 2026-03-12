import { cn, scoreBg } from "@/lib/utils";

interface ScoreBadgeProps {
  score?: number | null;
  size?: "sm" | "md" | "lg";
  label?: string;
}

export function ScoreBadge({ score, size = "md", label }: ScoreBadgeProps) {
  if (score == null) return <span className="text-text-muted text-xs">—</span>;

  const sizeClasses = {
    sm: "text-xs px-1.5 py-0.5 rounded font-mono",
    md: "text-sm px-2 py-0.5 rounded-md font-mono font-semibold",
    lg: "text-base px-3 py-1 rounded-lg font-mono font-bold",
  };

  return (
    <span className={cn(sizeClasses[size], scoreBg(score))}>
      {label && <span className="text-text-muted text-xs mr-1">{label}</span>}
      {score.toFixed(1)}
    </span>
  );
}

interface ScoreBarProps {
  score?: number | null;
  label: string;
  maxScore?: number;
}

export function ScoreBar({ score, label, maxScore = 10 }: ScoreBarProps) {
  const pct = score != null ? (score / maxScore) * 100 : 0;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-text-secondary">{label}</span>
        <ScoreBadge score={score} size="sm" />
      </div>
      <div className="h-1.5 bg-surface-border rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            pct >= 80 ? "bg-accent-green" :
            pct >= 60 ? "bg-accent-cyan" :
            pct >= 40 ? "bg-accent-amber" : "bg-accent-red"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
