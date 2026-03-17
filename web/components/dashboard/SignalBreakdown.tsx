"use client";

import { cn } from "@/lib/utils";
import type { SignalScore } from "@/lib/api";

interface SignalBreakdownProps {
  signals: SignalScore;
}

const signalConfig: Record<
  string,
  { label: string; maxValue: number; color: string }
> = {
  S1_friday_momentum: {
    label: "Friday Momentum",
    maxValue: 20,
    color: "bg-blue-500",
  },
  S2_volume_anomaly: {
    label: "Volume Anomaly",
    maxValue: 10,
    color: "bg-purple-500",
  },
  S3_vol_term_structure: {
    label: "Vol Term Structure",
    maxValue: 15,
    color: "bg-indigo-500",
  },
  S4_gap_momentum: {
    label: "Gap Momentum",
    maxValue: 15,
    color: "bg-cyan-500",
  },
  S5_cross_asset_stress: {
    label: "Cross-Asset Stress",
    maxValue: 15,
    color: "bg-teal-500",
  },
  C1_silver_sympathy: {
    label: "Silver Sympathy",
    maxValue: 5,
    color: "bg-emerald-500",
  },
  C2_equity_preposition: {
    label: "Equity Pre-position",
    maxValue: 10,
    color: "bg-green-500",
  },
  NLP_narrative_pressure: {
    label: "Narrative Pressure",
    maxValue: 12,
    color: "bg-orange-500",
  },
};

export function SignalBreakdown({ signals }: SignalBreakdownProps) {
  const sortedSignals = Object.entries(signals).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-3">
      {sortedSignals.map(([key, value]) => {
        const config = signalConfig[key] || {
          label: key.replace(/_/g, " "),
          maxValue: 20,
          color: "bg-gray-500",
        };
        const percentage = Math.min(
          100,
          Math.max(0, (Math.abs(value) / config.maxValue) * 100)
        );
        const isNegative = value < 0;

        return (
          <div key={key} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">{config.label}</span>
              <span
                className={cn(
                  "font-medium",
                  isNegative ? "text-red-600" : value > 0 ? "text-green-600" : "text-gray-400"
                )}
              >
                {value > 0 ? "+" : ""}
                {value}
              </span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-500",
                  isNegative ? "bg-red-400" : config.color
                )}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
