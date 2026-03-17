"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Trade, TradeStats } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  cn,
  formatCurrency,
  formatPercent,
  formatDate,
  formatDateTime,
  getPnLColor,
  getTradeStatusColor,
} from "@/lib/utils";
import { Plus, X, DollarSign, TrendingUp, Target, Clock } from "lucide-react";

export default function TradesPage() {
  const [showNewTrade, setShowNewTrade] = useState(false);
  const queryClient = useQueryClient();

  // Fetch trades
  const { data: trades, isLoading: tradesLoading } = useQuery({
    queryKey: ["trades"],
    queryFn: () => api.getTrades(),
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ["trade-stats"],
    queryFn: api.getTradeStats,
  });

  // Close trade mutation
  const closeTradeMutation = useMutation({
    mutationFn: ({
      tradeId,
      exitValue,
    }: {
      tradeId: number;
      exitValue: number;
    }) => api.closeTrade(tradeId, exitValue),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trades"] });
      queryClient.invalidateQueries({ queryKey: ["trade-stats"] });
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Trade Journal</h1>
          <p className="text-sm text-gray-500">
            Track your actual trades and performance
          </p>
        </div>
        <Button onClick={() => setShowNewTrade(true)}>
          <Plus size={16} className="mr-2" />
          Log Trade
        </Button>
      </div>

      {/* Stats Summary */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Total Trades"
            value={stats.total_trades}
            icon={Target}
          />
          <StatCard
            label="Open Trades"
            value={stats.open_trades}
            icon={Clock}
            color="text-blue-600"
          />
          <StatCard
            label="Win Rate"
            value={formatPercent(stats.win_rate)}
            icon={TrendingUp}
            color={stats.win_rate >= 0.5 ? "text-green-600" : "text-red-600"}
          />
          <StatCard
            label="Total P&L"
            value={formatCurrency(stats.total_pnl)}
            icon={DollarSign}
            color={getPnLColor(stats.total_pnl)}
          />
        </div>
      )}

      {/* Trades Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Trades</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {tradesLoading ? (
            <div className="text-center py-12 text-gray-500">
              Loading trades...
            </div>
          ) : trades && trades.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Entry Date
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Structure
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Contracts
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Entry Premium
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Exit Value
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      P&L
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Status
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {trades.map((trade) => (
                    <TradeRow
                      key={trade.id}
                      trade={trade}
                      onClose={(exitValue) =>
                        closeTradeMutation.mutate({
                          tradeId: trade.id,
                          exitValue,
                        })
                      }
                    />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <p>No trades logged yet.</p>
              <p className="text-sm mt-2">
                Click "Log Trade" to record your first trade.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* New Trade Modal */}
      {showNewTrade && (
        <NewTradeModal onClose={() => setShowNewTrade(false)} />
      )}
    </div>
  );
}

function StatCard({
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
    <div className="bg-white rounded-xl border border-gray-200 p-4">
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

function TradeRow({
  trade,
  onClose,
}: {
  trade: Trade;
  onClose: (exitValue: number) => void;
}) {
  const [showCloseForm, setShowCloseForm] = useState(false);
  const [exitValue, setExitValue] = useState("");

  const handleClose = () => {
    const value = parseFloat(exitValue);
    if (!isNaN(value) && value >= 0) {
      onClose(value);
      setShowCloseForm(false);
    }
  };

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 text-sm text-gray-900">
        {formatDate(trade.entry_date)}
      </td>
      <td className="px-4 py-3">
        <div>
          <p className="text-sm font-medium text-gray-900">{trade.structure}</p>
          {trade.strike && (
            <p className="text-xs text-gray-500">{trade.strike}</p>
          )}
        </div>
      </td>
      <td className="px-4 py-3 text-center text-sm text-gray-600">
        {trade.contracts}
      </td>
      <td className="px-4 py-3 text-right text-sm text-gray-900">
        {formatCurrency(trade.entry_premium)}
      </td>
      <td className="px-4 py-3 text-right text-sm text-gray-900">
        {trade.exit_value !== null
          ? formatCurrency(trade.exit_value)
          : "-"}
      </td>
      <td className="px-4 py-3 text-right">
        {trade.pnl_actual !== null ? (
          <span className={cn("text-sm font-medium", getPnLColor(trade.pnl_actual))}>
            {trade.pnl_actual >= 0 ? "+" : ""}
            {formatCurrency(trade.pnl_actual)}
          </span>
        ) : (
          <span className="text-gray-400">-</span>
        )}
      </td>
      <td className="px-4 py-3 text-center">
        <Badge className={getTradeStatusColor(trade.status)}>
          {trade.status}
        </Badge>
      </td>
      <td className="px-4 py-3 text-center">
        {trade.status === "OPEN" && (
          <>
            {showCloseForm ? (
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={exitValue}
                  onChange={(e) => setExitValue(e.target.value)}
                  placeholder="Exit $"
                  className="w-20 border rounded px-2 py-1 text-sm"
                  step="0.01"
                />
                <Button size="sm" onClick={handleClose}>
                  Save
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setShowCloseForm(false)}
                >
                  <X size={14} />
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowCloseForm(true)}
              >
                Close
              </Button>
            )}
          </>
        )}
      </td>
    </tr>
  );
}

function NewTradeModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    structure: "",
    entry_premium: "",
    contracts: "1",
    strike: "",
    notes: "",
  });

  const createTradeMutation = useMutation({
    mutationFn: (data: {
      structure: string;
      entry_date: string;
      entry_premium: number;
      contracts: number;
      strike?: string;
      notes?: string;
    }) => api.createTrade(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trades"] });
      queryClient.invalidateQueries({ queryKey: ["trade-stats"] });
      onClose();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createTradeMutation.mutate({
      structure: formData.structure,
      entry_date: new Date().toISOString(),
      entry_premium: parseFloat(formData.entry_premium),
      contracts: parseInt(formData.contracts),
      strike: formData.strike || undefined,
      notes: formData.notes || undefined,
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <Card className="w-full max-w-md mx-4">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Log New Trade</CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X size={18} />
          </Button>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Structure *
              </label>
              <input
                type="text"
                value={formData.structure}
                onChange={(e) =>
                  setFormData({ ...formData, structure: e.target.value })
                }
                placeholder="e.g., GLD ATM straddle"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gold-500"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Entry Premium *
                </label>
                <input
                  type="number"
                  value={formData.entry_premium}
                  onChange={(e) =>
                    setFormData({ ...formData, entry_premium: e.target.value })
                  }
                  placeholder="$0.00"
                  step="0.01"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gold-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Contracts
                </label>
                <input
                  type="number"
                  value={formData.contracts}
                  onChange={(e) =>
                    setFormData({ ...formData, contracts: e.target.value })
                  }
                  min="1"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gold-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Strike(s)
              </label>
              <input
                type="text"
                value={formData.strike}
                onChange={(e) =>
                  setFormData({ ...formData, strike: e.target.value })
                }
                placeholder="e.g., $265"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gold-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Notes
              </label>
              <textarea
                value={formData.notes}
                onChange={(e) =>
                  setFormData({ ...formData, notes: e.target.value })
                }
                placeholder="Trade rationale, observations..."
                rows={3}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gold-500"
              />
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                isLoading={createTradeMutation.isPending}
              >
                Log Trade
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
