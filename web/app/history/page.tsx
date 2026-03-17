"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { WRSChart } from "@/components/history/WRSChart";
import { OutcomeTable } from "@/components/history/OutcomeTable";
import { PredictionAccuracy } from "@/components/history/PredictionAccuracy";
import { AlertTriangle } from "lucide-react";

export default function HistoryPage() {
  const {
    data: history,
    isLoading: historyLoading,
    error: historyError,
  } = useQuery({
    queryKey: ["wrs-history"],
    queryFn: () => api.getWRSWithOutcomes(),
  });

  const { data: stats } = useQuery({
    queryKey: ["outcome-stats"],
    queryFn: async () => {
      // Calculate stats from history data
      if (!history) return null;
      const withOutcomes = history.filter((h) => h.outcome);
      const correct = withOutcomes.filter((h) => h.outcome?.outcome_correct).length;
      const avgGap =
        withOutcomes.reduce(
          (sum, h) => sum + Math.abs(h.outcome?.gap_percent || 0),
          0
        ) / (withOutcomes.length || 1);

      return {
        total_outcomes: withOutcomes.length,
        correct_predictions: correct,
        accuracy: withOutcomes.length > 0 ? correct / withOutcomes.length : 0,
        avg_gap_percent: avgGap,
      };
    },
    enabled: !!history,
  });

  if (historyLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gold-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading history...</p>
        </div>
      </div>
    );
  }

  if (historyError) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto" />
              <h3 className="mt-4 font-semibold">Unable to load history</h3>
              <p className="text-sm text-gray-600 mt-2">
                Make sure the API server is running.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const historyData = history || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Historical Analysis</h1>
        <p className="text-sm text-gray-500">
          Track WRS scores and prediction outcomes over time
        </p>
      </div>

      {/* Accuracy Stats */}
      {stats && (
        <PredictionAccuracy
          total={stats.total_outcomes}
          correct={stats.correct_predictions}
          accuracy={stats.accuracy}
          avgGap={stats.avg_gap_percent}
        />
      )}

      {/* WRS Time Series Chart */}
      <Card>
        <CardHeader>
          <CardTitle>WRS Score Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          {historyData.length > 0 ? (
            <WRSChart data={historyData} height={350} />
          ) : (
            <div className="text-center py-12 text-gray-500">
              No historical data available. Record your first analysis to start tracking.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Outcome Table */}
      <Card>
        <CardHeader>
          <CardTitle>Prediction History</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          <OutcomeTable data={historyData} />
        </CardContent>
      </Card>
    </div>
  );
}
