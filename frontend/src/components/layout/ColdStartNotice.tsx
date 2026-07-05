'use client';

import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { API_BASE } from '@/lib/api';

/**
 * Warm-up probe for the free-tier backend (Render spins down after idle and
 * takes 30-60 s to wake). Pings /health on mount; if it doesn't answer fast,
 * shows a banner until it does. Doubles as the warm-up request itself.
 */
export function ColdStartNotice() {
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let showTimer: ReturnType<typeof setTimeout> | null = null;

    async function probe(): Promise<boolean> {
      try {
        const res = await fetch(`${API_BASE}/health`, { cache: 'no-store' });
        return res.ok;
      } catch {
        return false;
      }
    }

    async function run() {
      // Only surface the banner if the first probe is slow/failing —
      // a warm backend answers well before this fires.
      showTimer = setTimeout(() => {
        if (!cancelled) setWaking(true);
      }, 2500);

      while (!cancelled) {
        const ok = await probe();
        if (ok) break;
        await new Promise((r) => setTimeout(r, 4000));
      }

      if (showTimer) clearTimeout(showTimer);
      if (!cancelled) setWaking(false);
    }

    run();
    return () => {
      cancelled = true;
      if (showTimer) clearTimeout(showTimer);
    };
  }, []);

  if (!waking) return null;

  return (
    <div className="fixed inset-x-0 top-14 z-30 flex items-center justify-center gap-2 border-b border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs text-amber-300 backdrop-blur md:top-0">
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      雲端伺服器喚醒中(免費方案閒置後休眠),約需 30-60 秒,喚醒後資料會自動載入…
    </div>
  );
}
