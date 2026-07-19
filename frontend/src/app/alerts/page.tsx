'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Bell, BellRing, Trash2, LogIn, ArrowUp, ArrowDown } from 'lucide-react';
import { useAlerts } from '@/hooks/useAlerts';
import { Skeleton } from '@/components/ui/skeleton';
import type { PriceAlertItem } from '@/lib/types';

function CondBadge({ a }: { a: PriceAlertItem }) {
  // Taiwan convention: 漲到/突破 = red, 跌到/跌破 = green.
  return a.condition === 'above' ? (
    <span className="flex items-center gap-1 rounded-md bg-red-500/10 px-2 py-0.5 text-xs text-red-400">
      <ArrowUp className="h-3 w-3" /> 漲到 {a.target_price}
    </span>
  ) : (
    <span className="flex items-center gap-1 rounded-md bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-400">
      <ArrowDown className="h-3 w-3" /> 跌到 {a.target_price}
    </span>
  );
}

function AlertRow({ a, onRemove }: { a: PriceAlertItem; onRemove: (id: number) => void }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900 p-3 sm:p-4">
      {a.active ? (
        <Bell className="h-4 w-4 shrink-0 text-slate-500" />
      ) : (
        <BellRing className="h-4 w-4 shrink-0 text-amber-400" />
      )}
      <Link href={`/stock/?id=${a.stock_id}`} className="w-28 shrink-0 hover:text-emerald-300">
        <span className="text-sm font-medium text-white">{a.name}</span>
        <span className="ml-1 font-mono text-xs text-slate-500">{a.stock_id}</span>
      </Link>
      <CondBadge a={a} />
      <span className="hidden text-xs text-slate-400 sm:block">
        現價 {a.close ?? '—'}
      </span>
      {!a.active && a.triggered_at && (
        <span className="hidden text-xs text-amber-400/80 md:block">
          已於 {a.triggered_at.slice(0, 10)} 觸發(當時 {a.triggered_price})
        </span>
      )}
      <button
        onClick={() => onRemove(a.id)}
        title="刪除"
        className="ml-auto shrink-0 text-slate-500 transition-colors hover:text-red-400"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}

export default function AlertsPage() {
  const { alerts, loading, loggedIn, remove } = useAlerts();
  const router = useRouter();

  if (!loggedIn) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-10 text-center">
          <Bell className="mx-auto mb-3 h-8 w-8 text-slate-600" />
          <p className="mb-4 text-sm text-slate-400">
            登入後可設定價格提醒,收盤後系統自動檢查,達標即在此通知。
          </p>
          <button
            onClick={() => router.push('/login')}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-500/20 px-4 py-2 text-sm font-medium text-emerald-300 hover:bg-emerald-500/30"
          >
            <LogIn className="h-4 w-4" /> 登入 / 註冊
          </button>
        </div>
      </div>
    );
  }

  const triggered = alerts.filter((a) => !a.active);
  const active = alerts.filter((a) => a.active);

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="mx-auto max-w-3xl px-4 py-8">
        <div className="mb-6">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
            <Bell className="h-6 w-6 text-emerald-400" /> 通知中心
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            價格提醒在每日收盤資料更新後自動檢查(約 14:40)。在個股頁點鈴鐺即可新增。
          </p>
        </div>

        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full bg-slate-800" />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-10 text-center text-sm text-slate-400">
            尚未設定任何提醒。到個股頁點「鈴鐺」按鈕,設定目標價後這裡會顯示追蹤狀態。
          </div>
        ) : (
          <div className="space-y-6">
            {triggered.length > 0 && (
              <section>
                <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-amber-400">
                  <BellRing className="h-4 w-4" /> 已觸發({triggered.length})
                </h2>
                <div className="space-y-2">
                  {triggered.map((a) => (
                    <AlertRow key={a.id} a={a} onRemove={remove} />
                  ))}
                </div>
              </section>
            )}
            {active.length > 0 && (
              <section>
                <h2 className="mb-2 text-sm font-semibold text-slate-300">監控中({active.length})</h2>
                <div className="space-y-2">
                  {active.map((a) => (
                    <AlertRow key={a.id} a={a} onRemove={remove} />
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
