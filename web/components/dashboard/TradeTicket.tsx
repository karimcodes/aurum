"use client";

import { cn } from "@/lib/utils";
import type { TradeRecommendation } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { CheckCircle, XCircle, AlertCircle, Eye } from "lucide-react";

interface TradeTicketProps {
  recommendation: TradeRecommendation;
}

const actionConfig: Record<
  string,
  { variant: "default" | "success" | "warning" | "danger" | "info"; icon: any }
> = {
  "NO TRADE": { variant: "default", icon: XCircle },
  "MONITOR ONLY": { variant: "info", icon: Eye },
  "SMALL POSITION": { variant: "warning", icon: AlertCircle },
  "STANDARD POSITION": { variant: "success", icon: CheckCircle },
  "MAXIMUM POSITION": { variant: "danger", icon: CheckCircle },
};

export function TradeTicket({ recommendation }: TradeTicketProps) {
  const config = actionConfig[recommendation.action] || {
    variant: "default",
    icon: AlertCircle,
  };
  const Icon = config.icon;
  const isNoTrade = ["NO TRADE", "MONITOR ONLY"].includes(recommendation.action);

  return (
    <div className="space-y-4">
      {/* Action Header */}
      <div className="flex items-center gap-3">
        <Icon
          size={24}
          className={cn(
            config.variant === "success" && "text-green-600",
            config.variant === "warning" && "text-yellow-600",
            config.variant === "danger" && "text-red-600",
            config.variant === "info" && "text-blue-600",
            config.variant === "default" && "text-gray-400"
          )}
        />
        <div>
          <Badge variant={config.variant} className="text-sm px-3 py-1">
            {recommendation.action}
          </Badge>
        </div>
      </div>

      {/* Reason */}
      <p className="text-sm text-gray-600">{recommendation.reason}</p>

      {/* Trade Details */}
      {!isNoTrade && recommendation.structure && (
        <div className="space-y-3 pt-3 border-t border-gray-100">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-xs text-gray-500 uppercase">
                Instrument
              </span>
              <p className="font-medium text-sm">{recommendation.instrument}</p>
            </div>
            <div>
              <span className="text-xs text-gray-500 uppercase">Strike</span>
              <p className="font-medium text-sm">{recommendation.strike}</p>
            </div>
          </div>

          <div>
            <span className="text-xs text-gray-500 uppercase">Structure</span>
            <p className="font-medium text-sm">{recommendation.structure}</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-xs text-gray-500 uppercase">Premium</span>
              <p className="font-medium text-sm">{recommendation.premium}</p>
            </div>
            <div>
              <span className="text-xs text-gray-500 uppercase">Max Loss</span>
              <p className="font-medium text-sm text-red-600">
                {recommendation.max_loss}
              </p>
            </div>
          </div>

          {/* Exit Rules */}
          {recommendation.exit_rules && recommendation.exit_rules.length > 0 && (
            <div className="pt-3 border-t border-gray-100">
              <span className="text-xs text-gray-500 uppercase">Exit Rules</span>
              <ul className="mt-2 space-y-1">
                {recommendation.exit_rules.map((rule, i) => (
                  <li key={i} className="text-xs text-gray-600 flex gap-2">
                    <span className="text-gray-400">→</span>
                    {rule}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
