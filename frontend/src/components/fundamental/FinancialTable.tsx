'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface FinancialTableProps {
  fundamentals: {
    pe_ratio?: number | null;
    pb_ratio?: number | null;
    eps?: number | null;
    roe?: number | null;
    roa?: number | null;
    revenue?: number | null;
    revenue_mom?: number | null;
    revenue_yoy?: number | null;
    gross_margin?: number | null;
    operating_margin?: number | null;
    net_margin?: number | null;
    market_cap?: number | null;
    dividend_yield?: number | null;
  };
  statements: {
    report_year: number;
    report_quarter: number;
    revenue?: number | null;
    gross_profit?: number | null;
    operating_income?: number | null;
    net_income?: number | null;
    eps?: number | null;
  }[];
}

function formatValue(value: number | null | undefined, suffix = '', decimals = 2) {
  if (value == null) return '—';
  return `${value.toFixed(decimals)}${suffix}`;
}

function formatLargeNumber(value: number | null | undefined) {
  if (value == null) return '—';
  if (Math.abs(value) >= 1e12) return `${(value / 1e12).toFixed(2)} 兆`;
  if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(2)} 億`;
  if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(0)} 萬`;
  return value.toLocaleString();
}

function colorClass(value: number | null | undefined) {
  if (value == null) return 'text-slate-400';
  if (value > 0) return 'text-emerald-400';
  if (value < 0) return 'text-red-400';
  return 'text-slate-300';
}

function Row({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <tr className="border-b border-slate-800 last:border-0">
      <td className="py-2 pr-4 text-sm text-slate-400">{label}</td>
      <td className={`py-2 text-right text-sm font-medium ${valueClass ?? 'text-white'}`}>
        {value}
      </td>
    </tr>
  );
}

export function FinancialTable({ fundamentals, statements }: FinancialTableProps) {
  const f = fundamentals ?? {};

  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardHeader>
        <CardTitle className="text-white">關鍵財務指標</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* Valuation */}
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              估值指標
            </h4>
            <table className="w-full">
              <tbody>
                <Row label="本益比 (PE)" value={formatValue(f.pe_ratio)} />
                <Row label="股價淨值比 (PB)" value={formatValue(f.pb_ratio)} />
                <Row
                  label="每股盈餘 (EPS)"
                  value={formatValue(f.eps)}
                  valueClass={colorClass(f.eps)}
                />
                <Row label="市值" value={formatLargeNumber(f.market_cap)} />
                <Row label="殖利率" value={formatValue(f.dividend_yield, '%')} />
              </tbody>
            </table>
          </div>

          {/* Profitability */}
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              獲利能力
            </h4>
            <table className="w-full">
              <tbody>
                <Row
                  label="ROE"
                  value={formatValue(f.roe, '%')}
                  valueClass={colorClass(f.roe)}
                />
                <Row
                  label="ROA"
                  value={formatValue(f.roa, '%')}
                  valueClass={colorClass(f.roa)}
                />
                <Row
                  label="毛利率"
                  value={formatValue(f.gross_margin, '%')}
                  valueClass={colorClass(f.gross_margin)}
                />
                <Row
                  label="營業利益率"
                  value={formatValue(f.operating_margin, '%')}
                  valueClass={colorClass(f.operating_margin)}
                />
                <Row
                  label="淨利率"
                  value={formatValue(f.net_margin, '%')}
                  valueClass={colorClass(f.net_margin)}
                />
              </tbody>
            </table>
          </div>

          {/* Revenue */}
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              營收概況
            </h4>
            <table className="w-full">
              <tbody>
                <Row label="最新營收" value={formatLargeNumber(f.revenue)} />
                <Row
                  label="月增率 (MoM)"
                  value={formatValue(f.revenue_mom, '%')}
                  valueClass={colorClass(f.revenue_mom)}
                />
                <Row
                  label="年增率 (YoY)"
                  value={formatValue(f.revenue_yoy, '%')}
                  valueClass={colorClass(f.revenue_yoy)}
                />
              </tbody>
            </table>
          </div>
        </div>

        {/* Quarterly statements table */}
        {statements && statements.length > 0 && (
          <div className="mt-6">
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              近期季報
            </h4>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="py-2 text-left font-medium text-slate-400">季度</th>
                    <th className="py-2 text-right font-medium text-slate-400">營收</th>
                    <th className="py-2 text-right font-medium text-slate-400">EPS</th>
                  </tr>
                </thead>
                <tbody>
                  {statements.slice(0, 8).map((s, idx) => (
                    <tr key={idx} className="border-b border-slate-800 last:border-0">
                      <td className="py-2 text-slate-300">
                        {s.report_year}Q{s.report_quarter}
                      </td>
                      <td className="py-2 text-right text-white">
                        {formatLargeNumber(s.revenue)}
                      </td>
                      <td className={`py-2 text-right font-medium ${colorClass(s.eps)}`}>
                        {formatValue(s.eps)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
