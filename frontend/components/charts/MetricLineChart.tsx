"use client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from "recharts";
import { format, parseISO } from "date-fns";
import { CHART_COLORS } from "@/lib/utils";
import type { MetricValue, MetricSeries } from "@/lib/api";

interface SingleMetricChartProps {
  data: MetricValue[];
  label: string;
  unit?: string;
  color?: string;
  height?: number;
}

export function SingleMetricChart({
  data,
  label,
  unit = "",
  color = "#3b82f6",
  height = 200,
}: SingleMetricChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-text-muted text-sm" style={{ height }}>
        No data available
      </div>
    );
  }

  const formatted = data
    .filter((d) => d.value != null)
    .map((d) => ({
      date: d.date,
      value: d.value,
      label: format(parseISO(d.date), "MMM ''yy"),
    }));

  const formatValue = (v: number) => {
    if (Math.abs(v) >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
    if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
    if (Math.abs(v) >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
    return v.toFixed(1);
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={formatted} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a3a5c" opacity={0.5} />
        <XAxis
          dataKey="label"
          tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "JetBrains Mono" }}
          axisLine={{ stroke: "#2a3a5c" }}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={formatValue}
          tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "JetBrains Mono" }}
          axisLine={false}
          tickLine={false}
          width={50}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#141b2d",
            border: "1px solid #2a3a5c",
            borderRadius: "8px",
            fontFamily: "JetBrains Mono",
            fontSize: "12px",
          }}
          formatter={(v: number) => [`${formatValue(v)} ${unit}`, label]}
          labelFormatter={(l) => l}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: color, stroke: "#0a0e1a", strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

interface MultiMetricChartProps {
  companies: MetricSeries[];
  unit?: string;
  height?: number;
  showGrowth?: boolean;
}

export function MultiMetricChart({
  companies,
  unit = "",
  height = 300,
  showGrowth = false,
}: MultiMetricChartProps) {
  if (!companies || companies.length === 0) {
    return (
      <div className="flex items-center justify-center text-text-muted text-sm" style={{ height }}>
        No data available
      </div>
    );
  }

  // Merge all dates
  const allDates = new Set<string>();
  companies.forEach((c) => c.values.forEach((v) => allDates.add(v.date)));
  const sortedDates = Array.from(allDates).sort();

  const chartData = sortedDates.map((date) => {
    const point: Record<string, unknown> = {
      date,
      label: format(parseISO(date), "MMM ''yy"),
    };
    companies.forEach((c) => {
      const found = c.values.find((v) => v.date === date);
      point[c.ticker] = showGrowth ? found?.yoy_growth : found?.value;
    });
    return point;
  });

  const formatValue = (v: number) => {
    if (showGrowth) return `${v.toFixed(1)}%`;
    if (Math.abs(v) >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
    if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
    if (Math.abs(v) >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
    return v.toFixed(1);
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a3a5c" opacity={0.5} />
        <XAxis
          dataKey="label"
          tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "JetBrains Mono" }}
          axisLine={{ stroke: "#2a3a5c" }}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={formatValue}
          tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "JetBrains Mono" }}
          axisLine={false}
          tickLine={false}
          width={55}
        />
        {showGrowth && <ReferenceLine y={0} stroke="#2a3a5c" strokeWidth={1} />}
        <Tooltip
          contentStyle={{
            backgroundColor: "#141b2d",
            border: "1px solid #2a3a5c",
            borderRadius: "8px",
            fontFamily: "JetBrains Mono",
            fontSize: "12px",
          }}
          formatter={(v: number, name: string) => [
            `${formatValue(v)} ${unit}`,
            name,
          ]}
        />
        <Legend
          wrapperStyle={{ fontSize: "12px", fontFamily: "JetBrains Mono", color: "#94a3b8" }}
        />
        {companies.map((company, i) => (
          <Line
            key={company.ticker}
            type="monotone"
            dataKey={company.ticker}
            stroke={CHART_COLORS[i % CHART_COLORS.length]}
            strokeWidth={2}
            dot={false}
            connectNulls
            activeDot={{ r: 4, strokeWidth: 2 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
