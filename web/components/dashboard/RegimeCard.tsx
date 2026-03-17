"use client";

import { Badge } from "@/components/ui/Badge";
import { cn, getRegimeBadgeColor, formatPercent } from "@/lib/utils";
import type { RegimeInfo } from "@/lib/api";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface RegimeCardProps {
  regime: RegimeInfo;
}

const regimeDescriptions: Record<string, string> = {
  MACRO_STRESS: "Elevated macro anxiety. Gold leading as safe haven.",
  AI_INFRA_CAPEX: "Industrial demand driving copper. Risk-on environment.",
  SPECULATIVE_ROTATION: "High dispersion. Speculative flows dominating.",
  LOW_VOL_STABILITY: "Low volatility regime. Limited weekend risk premium.",
  ENERGY_GEOPOLITICS: "Energy/geopolitical concerns. Mixed signals.",
  NORMAL: "Normal market conditions. Standard risk premium.",
  UNDETERMINED: "Insufficient data for regime classification.",
};

export function RegimeCard({ regime }: RegimeCardProps) {
  const description =
    regimeDescriptions[regime.regime] || "Unknown regime state.";

  return (
    <div className="space-y-4">
      {/* Regime Badge */}
      <div className="flex items-center justify-between">
        <Badge className={cn("px-3 py-1", getRegimeBadgeColor(regime.regime))}>
          {regime.regime.replace(/_/g, " ")}
        </Badge>
        <span
          className={cn(
            "text-sm font-medium",
            regime.sra > 0 ? "text-green-600" : regime.sra < 0 ? "text-red-600" : "text-gray-500"
          )}
        >
          SRA: {regime.sra > 0 ? "+" : ""}
          {regime.sra}
        </span>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-600">{description}</p>

      {/* Gold Rank */}
      <div className="flex items-center justify-between py-2 border-t border-gray-100">
        <span className="text-sm text-gray-500">Gold Rank</span>
        <span className="font-medium">
          #{regime.gold_rank} of {regime.stack_of}
        </span>
      </div>

      {/* Dispersion */}
      <div className="flex items-center justify-between py-2 border-t border-gray-100">
        <span className="text-sm text-gray-500">Dispersion</span>
        <span className="font-medium">{regime.dispersion.toFixed(4)}</span>
      </div>

      {/* Stack Returns */}
      <div className="pt-2 border-t border-gray-100">
        <h4 className="text-sm font-medium text-gray-700 mb-2">
          Metals Stack (21d)
        </h4>
        <div className="space-y-2">
          {regime.stack_returns.slice(0, 5).map(([name, ret]) => (
            <div
              key={name}
              className={cn(
                "flex items-center justify-between py-1.5 px-2 rounded",
                name === "Gold" ? "bg-gold-50" : "bg-gray-50"
              )}
            >
              <span
                className={cn(
                  "text-sm",
                  name === "Gold" ? "font-medium text-gold-800" : "text-gray-600"
                )}
              >
                {name}
              </span>
              <div className="flex items-center gap-1">
                {ret > 0 ? (
                  <TrendingUp size={14} className="text-green-500" />
                ) : ret < 0 ? (
                  <TrendingDown size={14} className="text-red-500" />
                ) : (
                  <Minus size={14} className="text-gray-400" />
                )}
                <span
                  className={cn(
                    "text-sm font-medium",
                    ret > 0 ? "text-green-600" : ret < 0 ? "text-red-600" : "text-gray-500"
                  )}
                >
                  {formatPercent(ret)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
