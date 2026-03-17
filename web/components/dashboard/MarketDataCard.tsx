"use client";

import { formatCurrency, formatPercent } from "@/lib/utils";
import type { MarketData } from "@/lib/api";

interface MarketDataCardProps {
  data: MarketData;
}

export function MarketDataCard({ data }: MarketDataCardProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
      <DataItem
        label="Gold (GLD)"
        value={formatCurrency(data.gold_price)}
        icon="🥇"
      />
      <DataItem
        label="Silver (SLV)"
        value={formatCurrency(data.silver_price)}
        icon="🥈"
      />
      <DataItem label="VIX (Spot)" value={data.vix.toFixed(2)} icon="📊" />
      <DataItem label="VXX (ETN)" value={data.vxx?.toFixed(2) || "N/A"} icon="📉" />
      <DataItem
        label="Au/Ag Ratio"
        value={data.gold_silver_ratio.toFixed(1)}
        icon="⚖️"
      />
      <DataItem
        label="Gold RV (21d)"
        value={`${data.gold_rv_21d.toFixed(1)}%`}
        icon="📈"
      />
    </div>
  );
}

function DataItem({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: string;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 text-center">
      <span className="text-2xl">{icon}</span>
      <p className="text-lg font-semibold mt-1">{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}
