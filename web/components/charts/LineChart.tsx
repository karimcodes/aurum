"use client";

import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { formatDate } from "@/lib/utils";

interface LineChartProps {
  data: any[];
  xKey: string;
  yKey: string;
  yKey2?: string;
  color?: string;
  color2?: string;
  height?: number;
  showLegend?: boolean;
  yDomain?: [number, number];
  formatX?: (value: any) => string;
  formatY?: (value: any) => string;
}

export function LineChart({
  data,
  xKey,
  yKey,
  yKey2,
  color = "#EAB308",
  color2 = "#3B82F6",
  height = 300,
  showLegend = false,
  yDomain,
  formatX,
  formatY,
}: LineChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsLineChart
        data={data}
        margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
        <XAxis
          dataKey={xKey}
          tickFormatter={formatX || ((value) => formatDate(value))}
          tick={{ fontSize: 12, fill: "#6B7280" }}
          tickLine={false}
          axisLine={{ stroke: "#E5E7EB" }}
        />
        <YAxis
          domain={yDomain}
          tickFormatter={formatY}
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
          labelFormatter={formatX || ((value) => formatDate(value))}
          formatter={(value: number) => [
            formatY ? formatY(value) : value.toFixed(2),
            "",
          ]}
        />
        {showLegend && <Legend />}
        <Line
          type="monotone"
          dataKey={yKey}
          stroke={color}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 6, fill: color }}
        />
        {yKey2 && (
          <Line
            type="monotone"
            dataKey={yKey2}
            stroke={color2}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6, fill: color2 }}
          />
        )}
      </RechartsLineChart>
    </ResponsiveContainer>
  );
}
