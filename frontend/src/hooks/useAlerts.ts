'use client';

import { useState, useEffect, useCallback } from 'react';
import { alertsAPI } from '@/lib/api';
import { useAuth } from './useAuth';
import type { PriceAlertItem } from '@/lib/types';

/** Per-user price alerts (requires login). */
export function useAlerts() {
  const { token, loggedIn } = useAuth();
  const [alerts, setAlerts] = useState<PriceAlertItem[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!token) {
      setAlerts([]);
      return;
    }
    setLoading(true);
    try {
      setAlerts(await alertsAPI.get());
    } catch {
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const create = useCallback(
    async (stockId: string, condition: 'above' | 'below', targetPrice: number) => {
      await alertsAPI.create(stockId, condition, targetPrice);
      await refresh();
    },
    [refresh],
  );

  const remove = useCallback(
    async (id: number) => {
      await alertsAPI.remove(id);
      await refresh();
    },
    [refresh],
  );

  const triggeredCount = alerts.filter((a) => !a.active).length;

  return { alerts, loading, loggedIn, refresh, create, remove, triggeredCount };
}
