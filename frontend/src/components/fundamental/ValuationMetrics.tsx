'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ValuationMetricsProps {
  fundamentals: {
    pe_ratio?: number | null;
    pb_ratio?: number | null;
    eps?: number | null;
    dividend_yield?: number | null;
    eps_growth?: number | null;
  };
  industry_avg: {
    pe_ratio?: number | null;
    pb_ratio?: number | null;
    eps?: number | null;
    dividend_yield?: number | null;
    eps_growth?: number | null;
  };
}

interface MetricCardProps {
  label: string;
  stockValue: number | null | undefined;
  industryValue: number | null | undefined;
  suffix?: string;
  lowerIsBetter?: boolean;
}

function MetricCard({
  label,
  stockValue,
  industryValue,
  suffix = '',
  lowerIsBetter = false,
}: MetricCardProps) {
  const hasComparison = stockValue != null && industryValue != null && industryValue !== 0;
  let comparisonText = '';
  let comparisonColor = 'text-slate-400';

  if (hasComparison) {
    const isAbove = stockValue! > industryValue!;
    comparisonText = isAbove ? '高於產業' : '低於產業';
    if (lowerIsBetter) {
      comparisonColor = isAbove ? 'text-red-400' : 'text-emerald-400';
    } else {
      comparisonColor = isAbove ? 'text-emerald-400' : 'text-red-400';
    }
  }

  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardContent className="pt-4">
        <div className="text-xs text-slate-400">{label}</div>
        <div className="mt-1 flex items-end justify-between">
          <div>
            <div className="text-xl font-bold text-white">
              {stockValue != null ? `${Number(stockValue).toFixed(2)}${suffix}` : '—'}
            </div>
            <div className="mt-0.5 text-xs text-slate-500">
              產業平均: {industryValue != null ? `${Number(industryValue).toFixed(2)}${suffix}` : '—'}
            </div>
          </div>
          {hasComparison && (
            <span className={`text-xs font-medium ${comparisonColor}`}>
              {comparisonText}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function ValuationMetrics({ fundamentals, industry_avg }: ValuationMetricsProps) {
  const f = fundamentals ?? {};
  const ind = industry_avg ?? {};

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-slate-300">估值比較</h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="本益比 (PE)"
          stockValue={f.pe_ratio}
          industryValue={ind.pe_ratio}
          lowerIsBetter
        />
        <MetricCard
          label="股價淨值比 (PB)"
          stockValue={f.pb_ratio}
          industryValue={ind.pb_ratio}
          lowerIsBetter
        />
        <MetricCard
          label="EPS 成長率"
          stockValue={f.eps_growth}
          industryValue={ind.eps_growth}
          suffix="%"
        />
        <MetricCard
          label="殖利率"
          stockValue={f.dividend_yield}
          industryValue={ind.dividend_yield}
          suffix="%"
        />
      </div>
    </div>
  );
}
