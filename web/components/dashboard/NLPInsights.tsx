"use client";

import { useQuery } from "@tanstack/react-query";
import { api, NLPAnalysisResponse } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  Newspaper,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Activity,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from "lucide-react";
import { useState } from "react";

export function NLPInsights() {
  const [expanded, setExpanded] = useState(false);

  const { data: nlp, isLoading, error } = useQuery({
    queryKey: ["nlp-analysis"],
    queryFn: api.getNLPAnalysis,
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 min
    staleTime: 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex items-center gap-2 text-gray-500">
          <Newspaper size={18} />
          <span>Loading news analysis...</span>
        </div>
      </div>
    );
  }

  if (error || !nlp) {
    return (
      <div className="bg-yellow-50 rounded-xl border border-yellow-200 p-4">
        <div className="flex items-center gap-2 text-yellow-700">
          <AlertTriangle size={18} />
          <span>NLP analysis unavailable</span>
        </div>
      </div>
    );
  }

  const directionIcon =
    nlp.direction === "escalating" ? (
      <TrendingUp className="text-red-500" size={18} />
    ) : nlp.direction === "de_escalating" ? (
      <TrendingDown className="text-green-500" size={18} />
    ) : (
      <Activity className="text-gray-500" size={18} />
    );

  const directionColor =
    nlp.direction === "escalating"
      ? "text-red-600"
      : nlp.direction === "de_escalating"
      ? "text-green-600"
      : "text-gray-600";

  const scoreBg =
    nlp.narrative_pressure_score > 8
      ? "bg-red-100 text-red-800"
      : nlp.narrative_pressure_score > 4
      ? "bg-yellow-100 text-yellow-800"
      : "bg-gray-100 text-gray-800";

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div
        className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Newspaper className="text-gold-600" size={20} />
            <span className="font-semibold text-gray-900">NLP Analysis</span>
            <span className={cn("px-2 py-0.5 rounded-full text-xs font-medium", scoreBg)}>
              {nlp.narrative_pressure_score.toFixed(1)} / 12
            </span>
          </div>
          <div className="flex items-center gap-3">
            {nlp.shift_detected && (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                SHIFT DETECTED
              </span>
            )}
            {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </div>
        </div>

        {/* Summary Row */}
        <div className="mt-3 grid grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Direction</span>
            <div className={cn("flex items-center gap-1 font-medium", directionColor)}>
              {directionIcon}
              {nlp.direction.replace("_", "-")}
            </div>
          </div>
          <div>
            <span className="text-gray-500">Headlines</span>
            <div className="font-medium">{nlp.relevant_headlines}</div>
          </div>
          <div>
            <span className="text-gray-500">Velocity</span>
            <div className={cn("font-medium", nlp.velocity_ratio > 2 ? "text-orange-600" : "")}>
              {nlp.velocity_ratio.toFixed(1)}x
            </div>
          </div>
          <div>
            <span className="text-gray-500">WRS Impact</span>
            <div className={cn("font-medium", nlp.wrs_contribution > 0 ? "text-red-600" : nlp.wrs_contribution < 0 ? "text-green-600" : "")}>
              {nlp.wrs_contribution > 0 ? "+" : ""}{nlp.wrs_contribution.toFixed(1)}
            </div>
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="border-t border-gray-100 p-4 space-y-4">
          {/* Interpretation */}
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-sm text-gray-700">{nlp.interpretation}</p>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <StatBox label="Escalation" value={nlp.escalation_count} color="text-red-600" />
            <StatBox label="De-escalation" value={nlp.deescalation_count} color="text-green-600" />
            <StatBox label="Theme" value={nlp.dominant_theme.split("_")[0]} />
            <StatBox label="Shift Type" value={nlp.shift_type || "None"} />
          </div>

          {/* Velocity Details */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-gray-50 rounded-lg p-2 text-center">
              <div className="text-xs text-gray-500">1h velocity</div>
              <div className="font-semibold">{nlp.velocity_1h.toFixed(1)}/hr</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-2 text-center">
              <div className="text-xs text-gray-500">6h velocity</div>
              <div className="font-semibold">{nlp.velocity_6h.toFixed(1)}/hr</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-2 text-center">
              <div className="text-xs text-gray-500">24h velocity</div>
              <div className="font-semibold">{nlp.velocity_24h.toFixed(1)}/hr</div>
            </div>
          </div>

          {/* Top Headlines */}
          {nlp.top_headlines.length > 0 && (
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Top Headlines</h4>
              <div className="space-y-2">
                {nlp.top_headlines.slice(0, 5).map((h, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 text-sm border-l-2 border-gold-500 pl-3 py-1"
                  >
                    <div className="flex-1">
                      <p className="text-gray-800">{h.headline}</p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {h.source} | Score: {h.score.toFixed(1)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sources */}
          <div className="text-xs text-gray-500">
            <span className="font-medium">Sources:</span>{" "}
            {nlp.sources_succeeded.slice(0, 5).join(", ")}
            {nlp.sources_failed.length > 0 && (
              <span className="text-yellow-600 ml-2">
                ({nlp.sources_failed.length} failed)
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StatBox({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-2 text-center">
      <div className="text-xs text-gray-500">{label}</div>
      <div className={cn("font-semibold", color)}>{value}</div>
    </div>
  );
}
