"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api, BacktestResponse, SignalAttribution } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { AreaChart } from "@/components/charts/AreaChart";
import { BarChart } from "@/components/charts/BarChart";
import {
  cn,
  formatCurrency,
  formatPercent,
  formatDate,
  getPnLColor,
} from "@/lib/utils";
import { Play, TrendingUp, TrendingDown, Target, BarChart3 } from "lucide-react";

export default function BacktestPage() {
  const [weeks, setWeeks] = useState(12);

  // Quick backtest query
  const {
    data: quickResult,
    isLoading: quickLoading,
    refetch: runQuickBacktest,
  } = useQuery({
    queryKey: ["quick-backtest", weeks],
    queryFn: () => api.getQuickBacktest(weeks),
    enabled: false,
  });

  // Signal attribution
  const { data: signals, isLoading: signalsLoading } = useQuery({
    queryKey: ["signal-attribution"],
    queryFn: api.getSignalAttribution,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Backtesting</h1>
        <p className="text-sm text-gray-500">
          Test the strategy on historical data
        </p>
      </div>

      {/* Quick Backtest Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Backtest</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <label className="text-sm text-gray-600 mb-1 block">
                Time Period
              </label>
              <select
                value={weeks}
                onChange={(e) => setWeeks(Number(e.target.value))}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gold-500"
              >
                <option value={4}>4 weeks</option>
                <option value={8}>8 weeks</option>
                <option value={12}>12 weeks</option>
                <option value={26}>26 weeks (6 months)</option>
                <option value={52}>52 weeks (1 year)</option>
              </select>
            </div>

            <Button
              onClick={() => runQuickBacktest()}
              isLoading={quickLoading}
              className="mt-auto"
            >
              <Play size={16} className="mr-2" />
              Run Backtest
            </Button>
          </div>

          {/* Quick Results */}
          {quickResult && (
            <div className="mt-6 grid grid-cols-2 md:grid-cols-5 gap-4">
              <StatBox
                label="Total Return"
                value={`${quickResult.total_return_pct >= 0 ? "+" : ""}${quickResult.total_return_pct.toFixed(1)}%`}
                icon={TrendingUp}
                color={
                  quickResult.total_return_pct >= 0
                    ? "text-green-600"
                    : "text-red-600"
                }
              />
              <StatBox
                label="Win Rate"
                value={`${quickResult.win_rate_pct.toFixed(0)}%`}
                icon={Target}
              />
              <StatBox
                label="Total Trades"
                value={quickResult.total_trades}
                icon={BarChart3}
              />
              <StatBox
                label="Max Drawdown"
                value={`-${quickResult.max_drawdown_pct.toFixed(1)}%`}
                icon={TrendingDown}
                color="text-red-600"
              />
              <StatBox
                label="Sharpe Ratio"
                value={quickResult.sharpe_ratio.toFixed(2)}
                icon={Target}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Signal Attribution */}
      <Card>
        <CardHeader>
          <CardTitle>Signal Performance Attribution</CardTitle>
        </CardHeader>
        <CardContent>
          {signalsLoading ? (
            <div className="text-center py-8 text-gray-500">
              Loading signal data...
            </div>
          ) : signals && signals.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Signal
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Times Fired
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Correct
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Accuracy
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Avg Contribution
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Avg Gap When Fired
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {signals.map((signal) => (
                    <tr key={signal.signal_name} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {signal.signal_name.replace(/_/g, " ")}
                      </td>
                      <td className="px-4 py-3 text-center text-sm text-gray-600">
                        {signal.total_fires}
                      </td>
                      <td className="px-4 py-3 text-center text-sm text-gray-600">
                        {signal.correct_fires}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <Badge
                          variant={
                            signal.accuracy >= 0.6
                              ? "success"
                              : signal.accuracy >= 0.4
                              ? "warning"
                              : "danger"
                          }
                        >
                          {formatPercent(signal.accuracy)}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-center text-sm text-gray-600">
                        {signal.avg_contribution.toFixed(1)}
                      </td>
                      <td className="px-4 py-3 text-center text-sm text-gray-600">
                        {formatPercent(signal.avg_gap_when_fired)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              No signal performance data available yet. Record outcomes to build
              signal attribution.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Instructions */}
      <Card>
        <CardHeader>
          <CardTitle>How Backtesting Works</CardTitle>
        </CardHeader>
        <CardContent className="prose prose-sm max-w-none">
          <ul className="text-gray-600 space-y-2">
            <li>
              The backtest simulates running AURUM on historical Fridays
            </li>
            <li>
              For each Friday, it computes the WRS and generates a trade
              recommendation
            </li>
            <li>
              P&L is calculated based on simulated weekend gaps (uses historical
              volatility as proxy)
            </li>
            <li>
              Position sizing follows the strategy rules (0.5-1.5% of capital)
            </li>
            <li>
              Win/loss is determined by whether the gap exceeded the option
              premium
            </li>
          </ul>
          <p className="mt-4 text-sm text-yellow-600 bg-yellow-50 p-3 rounded-lg">
            Note: These results use simplified assumptions and should not be
            taken as indicative of real trading performance.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function StatBox({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  icon: any;
  color?: string;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="flex items-center gap-2 text-gray-500 mb-1">
        <Icon size={16} />
        <span className="text-xs uppercase">{label}</span>
      </div>
      <p className={cn("text-2xl font-bold", color || "text-gray-900")}>
        {value}
      </p>
    </div>
  );
}
