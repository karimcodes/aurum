"use client";

import { cn, formatDate, formatPercent, getWRSColor, getRegimeBadgeColor } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import type { WRSHistory } from "@/lib/api";
import { CheckCircle, XCircle, Minus } from "lucide-react";

interface OutcomeTableProps {
  data: WRSHistory[];
}

export function OutcomeTable({ data }: OutcomeTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Date
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
              WRS
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Regime
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Recommendation
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
              Gap %
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
              Correct
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
              P&L
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.map((item) => (
            <tr key={item.id} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-sm text-gray-900">
                {formatDate(item.date)}
              </td>
              <td className="px-4 py-3 text-center">
                <span
                  className={cn(
                    "inline-flex items-center justify-center w-10 h-10 rounded-full font-semibold",
                    getWRSColor(item.wrs_score)
                  )}
                >
                  {Math.round(item.wrs_score)}
                </span>
              </td>
              <td className="px-4 py-3">
                <Badge className={getRegimeBadgeColor(item.regime_state)}>
                  {item.regime_state.replace(/_/g, " ")}
                </Badge>
              </td>
              <td className="px-4 py-3 text-sm text-gray-600">
                {item.recommendation}
              </td>
              <td className="px-4 py-3 text-center">
                {item.outcome ? (
                  <span
                    className={cn(
                      "text-sm font-medium",
                      item.outcome.gap_percent > 0
                        ? "text-green-600"
                        : item.outcome.gap_percent < 0
                        ? "text-red-600"
                        : "text-gray-500"
                    )}
                  >
                    {item.outcome.gap_direction === "UP" ? "+" : ""}
                    {formatPercent(item.outcome.gap_percent)}
                  </span>
                ) : (
                  <span className="text-gray-400">-</span>
                )}
              </td>
              <td className="px-4 py-3 text-center">
                {item.outcome ? (
                  item.outcome.outcome_correct ? (
                    <CheckCircle className="inline-block h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="inline-block h-5 w-5 text-red-500" />
                  )
                ) : (
                  <Minus className="inline-block h-5 w-5 text-gray-300" />
                )}
              </td>
              <td className="px-4 py-3 text-right">
                {item.outcome?.pnl_theoretical !== undefined ? (
                  <span
                    className={cn(
                      "text-sm font-medium",
                      item.outcome.pnl_theoretical > 0
                        ? "text-green-600"
                        : item.outcome.pnl_theoretical < 0
                        ? "text-red-600"
                        : "text-gray-500"
                    )}
                  >
                    {formatPercent(item.outcome.pnl_theoretical)}
                  </span>
                ) : (
                  <span className="text-gray-400">-</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No history records found. Start recording analyses to build history.
        </div>
      )}
    </div>
  );
}
