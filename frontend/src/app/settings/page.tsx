'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Settings as SettingsIcon, UserCircle, LogOut, LogIn, Wifi, WifiOff,
  Trash2, LineChart, Palette, Info, CheckCircle2,
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { healthAPI, API_BASE } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getChartDays, setChartDays, CHART_DAYS_OPTIONS } from '@/lib/prefs';

function Section({ title, icon: Icon, children }: { title: string; icon: React.ElementType; children: React.ReactNode }) {
  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base text-white">
          <Icon className="h-4 w-4 text-emerald-400" /> {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const { loggedIn, email, logout } = useAuth();
  const [health, setHealth] = useState<'checking' | 'ok' | 'down'>('checking');
  const [chartDays, setChartDaysState] = useState<number>(120);
  const [cleared, setCleared] = useState(false);

  // Read browser-stored prefs after mount (avoids SSR/hydration mismatch).
  useEffect(() => {
    const sync = () => setChartDaysState(getChartDays());
    sync();
  }, []);

  // Plain (non-memoised) handler — also used by the manual re-check button.
  async function pingHealth() {
    setHealth('checking');
    try {
      const r = await healthAPI.check();
      setHealth(r.status === 'ok' ? 'ok' : 'down');
    } catch {
      setHealth('down');
    }
  }

  useEffect(() => {
    let active = true;
    const run = async () => {
      try {
        const r = await healthAPI.check();
        if (active) setHealth(r.status === 'ok' ? 'ok' : 'down');
      } catch {
        if (active) setHealth('down');
      }
    };
    run();
    return () => { active = false; };
  }, []);

  function pickChartDays(d: number) {
    setChartDays(d);
    setChartDaysState(d);
  }

  function clearCache() {
    // Preserve auth; clear cached preferences/local state.
    const token = localStorage.getItem('auth_token');
    const em = localStorage.getItem('auth_email');
    localStorage.clear();
    if (token) localStorage.setItem('auth_token', token);
    if (em) localStorage.setItem('auth_email', em);
    setChartDaysState(getChartDays());
    setCleared(true);
    setTimeout(() => setCleared(false), 2500);
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="mx-auto max-w-3xl px-4 py-8">
        <div className="mb-6">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
            <SettingsIcon className="h-6 w-6 text-emerald-400" /> 設定
          </h1>
          <p className="mt-1 text-sm text-slate-400">帳號、顯示偏好與系統資訊。</p>
        </div>

        <div className="space-y-4">
          {/* Account */}
          <Section title="帳號" icon={UserCircle}>
            {loggedIn ? (
              <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                  <UserCircle className="h-5 w-5 shrink-0 text-emerald-400" />
                  <span className="truncate text-sm text-slate-200">{email}</span>
                </div>
                <button
                  onClick={logout}
                  className="flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:border-red-500/40 hover:text-red-400"
                >
                  <LogOut className="h-4 w-4" /> 登出
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-slate-400">尚未登入，登入後可雲端同步自選股。</span>
                <Link
                  href="/login"
                  className="flex shrink-0 items-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-1.5 text-sm text-emerald-300 transition-colors hover:bg-emerald-500/20"
                >
                  <LogIn className="h-4 w-4" /> 登入 / 註冊
                </Link>
              </div>
            )}
          </Section>

          {/* Display preferences */}
          <Section title="顯示偏好" icon={LineChart}>
            <div>
              <div className="mb-2 text-sm text-slate-300">個股預設 K 線區間</div>
              <div className="flex gap-2">
                {CHART_DAYS_OPTIONS.map((d) => (
                  <button
                    key={d}
                    onClick={() => pickChartDays(d)}
                    className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                      chartDays === d
                        ? 'bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/40'
                        : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                    }`}
                  >
                    {d} 日
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-slate-500">下次開啟個股頁時生效。</p>
            </div>
          </Section>

          {/* Appearance */}
          <Section title="外觀與配色" icon={Palette}>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-300">佈景主題</span>
              <span className="rounded-md bg-slate-800 px-2.5 py-1 text-xs text-slate-400">深色（目前僅此）</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-300">漲跌配色</span>
              <span className="text-xs">
                <span className="text-red-400">紅漲</span>
                <span className="mx-1 text-slate-500">/</span>
                <span className="text-emerald-400">綠跌</span>
                <span className="ml-1 text-slate-500">（台股慣例）</span>
              </span>
            </div>
          </Section>

          {/* System */}
          <Section title="系統與資料" icon={Info}>
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm text-slate-300">後端連線</span>
              <button
                onClick={pingHealth}
                className="flex items-center gap-1.5 text-xs"
                title="點擊重新檢查"
              >
                {health === 'ok' ? (
                  <><Wifi className="h-4 w-4 text-emerald-400" /><span className="text-emerald-400">正常</span></>
                ) : health === 'down' ? (
                  <><WifiOff className="h-4 w-4 text-red-400" /><span className="text-red-400">無法連線</span></>
                ) : (
                  <span className="text-slate-400">檢查中…</span>
                )}
              </button>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm text-slate-300">API 位址</span>
              <span className="max-w-[60%] truncate font-mono text-xs text-slate-500">{API_BASE}</span>
            </div>
            <div className="flex items-center justify-between gap-3 border-t border-slate-800 pt-3">
              <span className="text-sm text-slate-300">本機快取</span>
              <button
                onClick={clearCache}
                className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:border-red-500/40 hover:text-red-400"
              >
                {cleared ? (
                  <><CheckCircle2 className="h-4 w-4 text-emerald-400" /> 已清除</>
                ) : (
                  <><Trash2 className="h-4 w-4" /> 清除快取</>
                )}
              </button>
            </div>
          </Section>

          {/* About */}
          <Section title="關於" icon={Info}>
            <p className="text-sm leading-relaxed text-slate-400">
              股市智析 — 台股五維度 AI 分析平台。整合消息面、基本面、技術面、籌碼面與總經面，
              提供綜合評分與投資決策參考。
            </p>
            <p className="text-xs text-slate-500">資料來源：FinMind、Yahoo Finance、FRED。</p>
            <p className="text-xs text-slate-600">本平台所有分析僅供研究參考，不構成投資建議。</p>
          </Section>
        </div>
      </div>
    </div>
  );
}
