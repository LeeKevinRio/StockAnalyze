'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { LogIn, UserPlus, TrendingUp } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/hooks/useAuth';
import { GoogleSignInButton, GOOGLE_ENABLED } from '@/components/layout/GoogleSignInButton';

export default function LoginPage() {
  const router = useRouter();
  const { login, register, loginWithGoogle, loggedIn } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (loggedIn) router.replace('/watchlist');
  }, [loggedIn, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === 'login') await login(email.trim(), password);
      else await register(email.trim(), password);
      router.replace('/watchlist');
    } catch (err) {
      setError(err instanceof Error ? err.message : '發生錯誤');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/15">
            <TrendingUp className="h-6 w-6 text-emerald-400" />
          </div>
          <h1 className="text-xl font-bold text-white">{mode === 'login' ? '登入' : '註冊'}股市智析</h1>
          <p className="text-sm text-slate-400">登入後自選股會雲端同步、跨裝置保存</p>
        </div>

        <Card className="border-slate-800 bg-slate-900">
          <CardContent className="pt-6">
            {/* Google sign-in (shows only when configured) */}
            {GOOGLE_ENABLED && (
              <div className="mb-5">
                <GoogleSignInButton
                  onCredential={async (credential) => {
                    setError(null);
                    try {
                      await loginWithGoogle(credential);
                      router.replace('/watchlist');
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Google 登入失敗');
                    }
                  }}
                />
                <div className="my-4 flex items-center gap-3 text-xs text-slate-500">
                  <div className="h-px flex-1 bg-slate-800" /> 或 <div className="h-px flex-1 bg-slate-800" />
                </div>
              </div>
            )}

            {/* Tabs */}
            <div className="mb-5 grid grid-cols-2 gap-1 rounded-lg bg-slate-800 p-1">
              {(['login', 'register'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => { setMode(m); setError(null); }}
                  className={`rounded-md py-1.5 text-sm font-medium transition-colors ${mode === m ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}
                >
                  {m === 'login' ? '登入' : '註冊'}
                </button>
              ))}
            </div>

            <form onSubmit={submit} className="space-y-3">
              <div>
                <label className="mb-1 block text-xs text-slate-400">Email</label>
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="border-slate-700 bg-slate-800 text-white placeholder:text-slate-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-400">密碼{mode === 'register' && '（至少 6 碼）'}</label>
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={6}
                  className="border-slate-700 bg-slate-800 text-white placeholder:text-slate-500"
                />
              </div>

              {error && <p className="text-sm text-red-400">{error}</p>}

              <button
                type="submit"
                disabled={busy}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500 disabled:opacity-60"
              >
                {mode === 'login' ? <LogIn className="h-4 w-4" /> : <UserPlus className="h-4 w-4" />}
                {busy ? '處理中…' : mode === 'login' ? '登入' : '註冊並登入'}
              </button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
