"use client";
import { useEffect, useState } from "react";
import { compareMetric, type MetricComparison } from "@/lib/api";
import { MultiMetricChart } from "@/components/charts/MetricLineChart";
import { Factory, Zap, Car, Cpu, Cloud } from "lucide-react";
import { cn } from "@/lib/utils";

interface IndustryTracker {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  metrics: {
    metric: string;
    label: string;
    unit: string;
    tickers: string[];
  }[];
}

const INDUSTRY_TRACKERS: IndustryTracker[] = [
  {
    id: "ai",
    name: "AI Infrastructure Buildout",
    description: "Tracking the global AI infrastructure arms race across hyperscalers and chipmakers",
    icon: <Cpu size={18} />,
    color: "#3b82f6",
    metrics: [
      {
        metric: "ai_capex_total",
        label: "AI/Datacenter Capex ($B)",
        unit: "$B",
        tickers: ["MSFT", "AMZN", "GOOGL", "META"],
      },
      {
        metric: "nvda_datacenter_revenue",
        label: "NVIDIA Datacenter Revenue",
        unit: "$M",
        tickers: ["NVDA"],
      },
      {
        metric: "datacenter_capacity_mw",
        label: "Datacenter Capacity (MW)",
        unit: "MW",
        tickers: ["AMZN", "MSFT", "GOOGL", "META"],
      },
    ],
  },
  {
    id: "cloud",
    name: "Cloud Computing Growth",
    description: "AWS, Azure, and Google Cloud revenue trajectories",
    icon: <Cloud size={18} />,
    color: "#06b6d4",
    metrics: [
      {
        metric: "amzn_aws_revenue",
        label: "AWS Revenue ($M)",
        unit: "$M",
        tickers: ["AMZN"],
      },
      {
        metric: "msft_cloud_revenue",
        label: "Azure / Intelligent Cloud Revenue ($M)",
        unit: "$M",
        tickers: ["MSFT"],
      },
      {
        metric: "googl_cloud_revenue",
        label: "Google Cloud Revenue ($M)",
        unit: "$M",
        tickers: ["GOOGL"],
      },
    ],
  },
  {
    id: "ev",
    name: "Electric Vehicle Ecosystem",
    description: "EV production, deliveries, and charging infrastructure buildout",
    icon: <Car size={18} />,
    color: "#22c55e",
    metrics: [
      {
        metric: "tsla_vehicle_deliveries",
        label: "Tesla Vehicle Deliveries",
        unit: "units",
        tickers: ["TSLA"],
      },
      {
        metric: "tsla_supercharger_sites",
        label: "Tesla Supercharger Sites",
        unit: "count",
        tickers: ["TSLA"],
      },
      {
        metric: "tsla_battery_storage_gwh",
        label: "Tesla Energy Storage (GWh)",
        unit: "GWh",
        tickers: ["TSLA"],
      },
    ],
  },
  {
    id: "semiconductor",
    name: "Semiconductor Leaders",
    description: "Revenue and margin trajectories for semiconductor companies",
    icon: <Zap size={18} />,
    color: "#a855f7",
    metrics: [
      {
        metric: "nvda_datacenter_revenue",
        label: "NVIDIA Datacenter Revenue",
        unit: "$M",
        tickers: ["NVDA"],
      },
      {
        metric: "nvda_gross_margin",
        label: "Gross Margin Comparison",
        unit: "%",
        tickers: ["NVDA", "AMD", "INTC", "AVGO"],
      },
      {
        metric: "r_and_d_spend",
        label: "R&D Spending ($M)",
        unit: "$M",
        tickers: ["NVDA", "AMD", "INTC", "AVGO", "QCOM"],
      },
    ],
  },
];

function IndustrySection({ tracker }: { tracker: IndustryTracker }) {
  const [activeMetric, setActiveMetric] = useState(0);
  const [data, setData] = useState<MetricComparison | null>(null);
  const [loading, setLoading] = useState(false);

  const metric = tracker.metrics[activeMetric];

  useEffect(() => {
    if (!metric) return;
    setLoading(true);
    compareMetric(metric.metric, metric.tickers, 5)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [metric]);

  return (
    <div className="bg-surface-1 border border-surface-border rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-surface-border">
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: `${tracker.color}20`, color: tracker.color }}
          >
            {tracker.icon}
          </div>
          <div>
            <h2 className="text-sm font-bold text-text-primary">{tracker.name}</h2>
            <p className="text-xs text-text-muted">{tracker.description}</p>
          </div>
        </div>
      </div>

      {/* Metric tabs */}
      <div className="flex gap-0 border-b border-surface-border bg-surface-2/30 px-4 pt-2">
        {tracker.metrics.map((m, i) => (
          <button
            key={m.metric}
            onClick={() => setActiveMetric(i)}
            className={cn(
              "px-3 py-2 text-xs font-medium border-b-2 transition-colors mr-2",
              activeMetric === i
                ? "border-current text-text-primary"
                : "border-transparent text-text-muted hover:text-text-secondary"
            )}
            style={activeMetric === i ? { borderColor: tracker.color, color: tracker.color } : {}}
          >
            {m.label.split(" ").slice(0, 3).join(" ")}
          </button>
        ))}
      </div>

      <div className="p-5">
        {/* Companies shown */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {metric.tickers.map((t) => (
            <span
              key={t}
              className="text-xs font-mono px-2 py-0.5 rounded"
              style={{ backgroundColor: `${tracker.color}15`, color: tracker.color, border: `1px solid ${tracker.color}25` }}
            >
              {t}
            </span>
          ))}
          <span className="text-xs text-text-muted ml-1">· {metric.unit}</span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-52 text-text-muted text-sm">
            <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mr-3" />
            Loading chart...
          </div>
        ) : data ? (
          <MultiMetricChart
            companies={data.companies}
            unit={metric.unit}
            height={240}
          />
        ) : (
          <div className="flex items-center justify-center h-52 text-text-muted text-sm">
            No data available
          </div>
        )}
      </div>
    </div>
  );
}

export default function IndustryPage() {
  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
          <Factory size={22} className="text-accent-orange" />
          Industry Build-Out Trackers
        </h1>
        <p className="text-text-muted text-sm mt-1">
          Cross-company dashboards tracking major infrastructure and technology buildouts
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        {INDUSTRY_TRACKERS.map((tracker) => (
          <IndustrySection key={tracker.id} tracker={tracker} />
        ))}
      </div>
    </div>
  );
}
