'use client';

import { useState, useEffect, useCallback } from 'react';
import { watchlistAPI } from '@/lib/api';
import { useAuth } from './useAuth';

const EVENT = 'watchlist-change';

/**
 * Per-user watchlist stored in the database (requires login).
 * When not logged in, the list is empty and `toggle` returns false so callers
 * can redirect to the login page.
 */
export function useWatchlist() {
  const { token, loggedIn } = useAuth();
  const [ids, setIds] = useState<string[]>([]);

  const refresh = useCallback(async () => {
    if (!token) {
      setIds([]);
      return;
    }
    try {
      setIds(await watchlistAPI.get());
    } catch {
      setIds([]);
    }
  }, [token]);

  useEffect(() => {
    refresh();
    const sync = () => refresh();
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, [refresh]);

  const has = useCallback((id: string) => ids.includes(id), [ids]);

  const toggle = useCallback(
    async (id: string): Promise<boolean> => {
      if (!token) return false; // caller should redirect to /login
      const isIn = ids.includes(id);
      setIds((prev) => (isIn ? prev.filter((x) => x !== id) : [...prev, id])); // optimistic
      try {
        if (isIn) await watchlistAPI.remove(id);
        else await watchlistAPI.add(id);
      } catch {
        refresh(); // revert on failure
      }
      window.dispatchEvent(new Event(EVENT));
      return true;
    },
    [token, ids, refresh],
  );

  return { ids, has, toggle, loggedIn, refresh };
}
