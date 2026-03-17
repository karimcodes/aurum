"use client";

import { cn } from "@/lib/utils";
import { getWRSLabel, getWRSColor } from "@/lib/utils";

interface WRSGaugeProps {
  score: number;
  adjustedScore?: number;
  sra?: number;
  size?: "sm" | "md" | "lg";
}

export function WRSGauge({
  score,
  adjustedScore,
  sra,
  size = "lg",
}: WRSGaugeProps) {
  const displayScore = adjustedScore ?? score;
  const radius = size === "lg" ? 80 : size === "md" ? 60 : 40;
  const strokeWidth = size === "lg" ? 12 : size === "md" ? 10 : 8;
  const circumference = 2 * Math.PI * radius;
  const halfCircumference = circumference / 2;
  const progress = (displayScore / 100) * halfCircumference;

  // Color gradient based on score
  const getGaugeColor = (score: number) => {
    if (score < 21) return "#9CA3AF"; // gray
    if (score < 41) return "#3B82F6"; // blue
    if (score < 61) return "#EAB308"; // yellow
    if (score < 81) return "#F97316"; // orange
    return "#EF4444"; // red
  };

  const gaugeColor = getGaugeColor(displayScore);
  const label = getWRSLabel(displayScore);

  const viewBoxSize = (radius + strokeWidth) * 2;
  const center = radius + strokeWidth;

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <svg
          width={viewBoxSize}
          height={radius + strokeWidth + 20}
          viewBox={`0 0 ${viewBoxSize} ${radius + strokeWidth + 20}`}
        >
          {/* Background arc */}
          <path
            d={`M ${strokeWidth} ${center} A ${radius} ${radius} 0 0 1 ${
              viewBoxSize - strokeWidth
            } ${center}`}
            fill="none"
            stroke="#E5E7EB"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Progress arc */}
          <path
            d={`M ${strokeWidth} ${center} A ${radius} ${radius} 0 0 1 ${
              viewBoxSize - strokeWidth
            } ${center}`}
            fill="none"
            stroke={gaugeColor}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={halfCircumference}
            strokeDashoffset={halfCircumference - progress}
            className="gauge-progress"
            style={{ transition: "stroke-dashoffset 1s ease-out" }}
          />

          {/* Score zones markers */}
          {[20, 40, 60, 80].map((zone) => {
            const angle = (zone / 100) * 180;
            const radians = (angle * Math.PI) / 180;
            const x =
              center - Math.cos(radians) * (radius + strokeWidth / 2 + 8);
            const y =
              center - Math.sin(radians) * (radius + strokeWidth / 2 + 8);
            return (
              <circle
                key={zone}
                cx={x}
                cy={y}
                r={2}
                fill="#9CA3AF"
                opacity={0.5}
              />
            );
          })}
        </svg>

        {/* Center text */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center"
          style={{ paddingTop: size === "lg" ? "20px" : "10px" }}
        >
          <span
            className={cn(
              "font-bold",
              size === "lg" ? "text-5xl" : size === "md" ? "text-3xl" : "text-2xl",
              getWRSColor(displayScore)
            )}
          >
            {Math.round(displayScore)}
          </span>
          {size !== "sm" && (
            <span className="text-sm text-gray-500 mt-1">{label}</span>
          )}
        </div>
      </div>

      {/* SRA adjustment info */}
      {sra !== undefined && sra !== 0 && (
        <div className="mt-2 text-center">
          <span className="text-xs text-gray-500">
            Raw: {Math.round(score)} | Regime: {sra > 0 ? "+" : ""}
            {sra}
          </span>
        </div>
      )}
    </div>
  );
}
