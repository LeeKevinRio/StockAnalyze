'use client';

import { useEffect, useRef } from 'react';
import type { StockPrice } from '@/lib/types';

interface PriceChartProps {
  prices: StockPrice[];
  height?: number;
}

export function PriceChart({ prices, height = 400 }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof import('lightweight-charts').createChart> | null>(null);

  useEffect(() => {
    if (!containerRef.current || prices.length === 0) return;

    let disposed = false;

    async function initChart() {
      const {
        createChart,
        CandlestickSeries,
        HistogramSeries,
      } = await import('lightweight-charts');

      if (disposed || !containerRef.current) return;

      // Clean up previous chart
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }

      const chart = createChart(containerRef.current, {
        height,
        layout: {
          background: { color: '#0f172a' },
          textColor: '#94a3b8',
          fontSize: 12,
        },
        grid: {
          vertLines: { color: '#1e293b' },
          horzLines: { color: '#1e293b' },
        },
        crosshair: {
          vertLine: { color: '#475569', width: 1, labelBackgroundColor: '#334155' },
          horzLine: { color: '#475569', width: 1, labelBackgroundColor: '#334155' },
        },
        rightPriceScale: {
          borderColor: '#1e293b',
          scaleMargins: { top: 0.1, bottom: 0.25 },
        },
        timeScale: {
          borderColor: '#1e293b',
          timeVisible: false,
          fixLeftEdge: true,
          fixRightEdge: true,
          lockVisibleTimeRangeOnResize: true,
        },
        // Only ~6 months of data — lock the view so it can't be zoomed/panned
        // away into empty space.
        handleScroll: false,
        handleScale: false,
      });

      chartRef.current = chart;

      // Sort prices by date
      const sorted = [...prices]
        .filter((p) => p.open != null && p.high != null && p.low != null && p.close != null)
        .sort((a, b) => a.date.localeCompare(b.date));

      // Candlestick series
      // Taiwan convention (紅漲綠跌): up candles red, down candles green.
      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: '#ef4444',
        downColor: '#22c55e',
        borderUpColor: '#ef4444',
        borderDownColor: '#22c55e',
        wickUpColor: '#ef4444',
        wickDownColor: '#22c55e',
      });

      const candleData = sorted.map((p) => ({
        time: p.date as string,
        open: Number(p.open),
        high: Number(p.high),
        low: Number(p.low),
        close: Number(p.close),
      }));

      candleSeries.setData(candleData);

      // Volume histogram series
      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      });

      chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      const volumeData = sorted
        .filter((p) => p.volume != null)
        .map((p) => ({
          time: p.date as string,
          value: p.volume!,
          color:
            p.close != null && p.open != null
              ? Number(p.close) >= Number(p.open)
                ? 'rgba(239,68,68,0.4)'
                : 'rgba(34,197,94,0.4)'
              : 'rgba(148,163,184,0.3)',
        }));

      volumeSeries.setData(volumeData);

      // Fit content
      chart.timeScale().fitContent();

      // Responsive resize
      const resizeObserver = new ResizeObserver((entries) => {
        if (entries[0] && chartRef.current) {
          const { width } = entries[0].contentRect;
          chartRef.current.applyOptions({ width });
        }
      });

      resizeObserver.observe(containerRef.current!);

      // Return cleanup for the resize observer
      return () => {
        resizeObserver.disconnect();
      };
    }

    let cleanupResize: (() => void) | undefined;
    initChart().then((cleanup) => {
      cleanupResize = cleanup;
    });

    return () => {
      disposed = true;
      cleanupResize?.();
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [prices, height]);

  if (prices.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg bg-slate-900 text-slate-400"
        style={{ height }}
      >
        尚無價格資料
      </div>
    );
  }

  return <div ref={containerRef} className="w-full rounded-lg" />;
}
