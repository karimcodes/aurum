"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { WRSGauge } from "@/components/dashboard/WRSGauge";
import { SignalBreakdown } from "@/components/dashboard/SignalBreakdown";
import { RegimeCard } from "@/components/dashboard/RegimeCard";
import { TradeTicket } from "@/components/dashboard/TradeTicket";
import { MarketDataCard } from "@/components/dashboard/MarketDataCard";
import { NLPInsights } from "@/components/dashboard/NLPInsights";
import { EventCalendar } from "@/components/dashboard/EventCalendar";
import { RefreshCw, AlertTriangle } from "lucide-react";
import { formatDateTime } from "@/lib/utils";

export default function Dashboard() {
  const {
    data: analysis,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["analysis"],
    queryFn: api.getCurrentAnalysis, // Use live data from Yahoo Finance
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
    staleTime: 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gold-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading analysis...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto" />
              <h3 className="mt-4 font-semibold">Unable to load analysis</h3>
              <p className="text-sm text-gray-600 mt-2">
                Make sure the API server is running on port 8000.
              </p>
              <Button onClick={() => refetch()} className="mt-4">
                Try Again
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!analysis) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Weekend Risk Dashboard
          </h1>
          <p className="text-sm text-gray-500">
            Last updated: {formatDateTime(analysis.timestamp)}
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => refetch()}
          isLoading={isFetching}
        >
          <RefreshCw size={16} className="mr-2" />
          Refresh
        </Button>
      </div>

      {/* Warnings */}
      {analysis.warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
            <div>
              <h4 className="font-medium text-yellow-800">Warnings</h4>
              <ul className="mt-1 text-sm text-yellow-700">
                {analysis.warnings.map((warning, i) => (
                  <li key={i}>{warning}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Market Data */}
      <MarketDataCard data={analysis.market_data} />

      {/* Intelligence Row - NLP & Events */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <NLPInsights />
        <EventCalendar />
      </div>

      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* WRS Gauge - Center */}
        <Card className="lg:col-span-1 lg:row-span-2">
          <CardHeader>
            <CardTitle>Weekend Risk Score</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center py-8">
            <WRSGauge
              score={analysis.wrs_score}
              adjustedScore={analysis.adjusted_wrs}
              sra={analysis.regime.sra}
              size="lg"
            />
          </CardContent>
        </Card>

        {/* Signal Breakdown */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Signal Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <SignalBreakdown signals={analysis.signals} />
          </CardContent>
        </Card>

        {/* Regime Info */}
        <Card>
          <CardHeader>
            <CardTitle>Market Regime</CardTitle>
          </CardHeader>
          <CardContent>
            <RegimeCard regime={analysis.regime} />
          </CardContent>
        </Card>

        {/* Trade Recommendation */}
        <Card>
          <CardHeader>
            <CardTitle>Trade Recommendation</CardTitle>
          </CardHeader>
          <CardContent>
            <TradeTicket recommendation={analysis.recommendation} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
