"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { formatDate } from "@/lib/utils";
import type { WRSHistory } from "@/lib/api";

interface WRSChartProps {
  data: WRSHistory[];
  height?: number;
}

export function WRSChart({ data, height = 300 }: WRSChartProps) {
  const chartData = data
    .map((item) => ({
      date: item.date,
      wrs: item.wrs_score,
      regime: item.regime_state,
    }))
    .reverse();

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart
        data={chartData}
        margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
        <XAxis
          dataKey="date"
          tickFormatter={(value) => formatDate(value)}
          tick={{ fontSize: 12, fill: "#6B7280" }}
          tickLine={false}
          axisLine={{ stroke: "#E5E7EB" }}
        />
        <YAxis
          domain={[0, 100]}
          ticks={[0, 20, 40, 60, 80, 100]}
          tick={{ fontSize: 12, fill: "#6B7280" }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "white",
            border: "1px solid #E5E7EB",
            borderRadius: "8px",
            fontSize: "12px",
          }}
          labelFormatter={(value) => formatDate(value)}
          formatter={(value: number, name: string) => [
            value.toFixed(0),
            "WRS",
          ]}
        />

        {/* Zone reference lines */}
        <ReferenceLine y={20} stroke="#9CA3AF" strokeDasharray="3 3" />
        <ReferenceLine y={40} stroke="#3B82F6" strokeDasharray="3 3" />
        <ReferenceLine y={60} stroke="#EAB308" strokeDasharray="3 3" />
        <ReferenceLine y={80} stroke="#F97316" strokeDasharray="3 3" />

        <Line
          type="monotone"
          dataKey="wrs"
          stroke="#EAB308"
          strokeWidth={2}
          dot={{ r: 4, fill: "#EAB308" }}
          activeDot={{ r: 6, fill: "#EAB308" }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
