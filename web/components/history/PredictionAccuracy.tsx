"use client";

import { cn, formatPercent } from "@/lib/utils";

interface PredictionAccuracyProps {
  total: number;
  correct: number;
  accuracy: number;
  avgGap: number;
}

export function PredictionAccuracy({
  total,
  correct,
  accuracy,
  avgGap,
}: PredictionAccuracyProps) {
  const getAccuracyColor = (acc: number) => {
    if (acc >= 0.7) return "text-green-600";
    if (acc >= 0.5) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard label="Total Predictions" value={total} />
      <StatCard label="Correct Predictions" value={correct} />
      <StatCard
        label="Accuracy"
        value={formatPercent(accuracy)}
        className={getAccuracyColor(accuracy)}
      />
      <StatCard label="Avg Gap" value={formatPercent(avgGap)} />
    </div>
  );
}

function StatCard({
  label,
  value,
  className,
}: {
  label: string;
  value: string | number;
  className?: string;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-4 text-center">
      <p className={cn("text-2xl font-bold", className || "text-gray-900")}>
        {value}
      </p>
      <p className="text-sm text-gray-500 mt-1">{label}</p>
    </div>
  );
}
