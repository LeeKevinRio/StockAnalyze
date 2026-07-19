'use client';

import { useState, useEffect, useCallback } from 'react';
import { portfolioAPI } from '@/lib/api';
import { useAuth } from './useAuth';
import type { PortfolioHolding } from '@/lib/types';

/** Per-user portfolio holdings (requires login). */
export function usePortfolio() {
  const { token, loggedIn } = useAuth();
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!token) {
      setHoldings([]);
      return;
    }
    setLoading(true);
    try {
      setHoldings(await portfolioAPI.get());
    } catch {
      setHoldings([]);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const upsert = useCallback(
    async (stockId: string, quantity: number, avgCost: number) => {
      await portfolioAPI.upsert(stockId, quantity, avgCost);
      await refresh();
    },
    [refresh],
  );

  const remove = useCallback(
    async (stockId: string) => {
      await portfolioAPI.remove(stockId);
      await refresh();
    },
    [refresh],
  );

  return { holdings, loading, loggedIn, refresh, upsert, remove };
}
