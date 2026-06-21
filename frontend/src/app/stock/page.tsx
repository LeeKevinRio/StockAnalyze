'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { Loading } from '@/components/common/Loading';
import StockPageClient from './StockPageClient';

function StockContent() {
  const searchParams = useSearchParams();
  const stockId = searchParams.get('id');

  if (!stockId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <p className="text-slate-400">請輸入股票代號</p>
      </div>
    );
  }

  // key forces a clean remount when the id changes (avoids stale state when
  // navigating stock→stock).
  return <StockPageClient key={stockId} stockId={stockId} />;
}

export default function StockPage() {
  return (
    <Suspense fallback={<Loading />}>
      <StockContent />
    </Suspense>
  );
}
