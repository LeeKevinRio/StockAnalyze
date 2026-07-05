/**
 * Taiwan / Asian market colour convention: 紅漲綠跌.
 *
 * RED  = up / bullish / positive / 看多 / 漲
 * GREEN = down / bearish / negative / 看空 / 跌
 *
 * This is the OPPOSITE of the Western convention. Keep all directional
 * (price / score / sentiment) colours flowing through these helpers so the
 * whole app stays consistent. Non-directional brand accents (buttons, links)
 * may still use emerald as a neutral brand colour.
 */

export const UP_HEX = '#ef4444';        // red-500  — bullish / up
export const UP_HEX_SOFT = '#f87171';   // red-400
export const DOWN_HEX = '#22c55e';      // green-500 — bearish / down
export const DOWN_HEX_SOFT = '#4ade80'; // green-400
export const NEUTRAL_HEX = '#94a3b8';   // slate-400

/** Hex colour for a score in [-100, 100] (red = high/bullish). */
export function scoreHex(score: number): string {
  if (score >= 60) return UP_HEX;
  if (score >= 20) return UP_HEX_SOFT;
  if (score >= -20) return NEUTRAL_HEX;
  if (score >= -60) return DOWN_HEX_SOFT;
  return DOWN_HEX;
}

/** Tailwind text-colour class for a score in [-100, 100]. */
export function scoreTextClass(score: number): string {
  if (score >= 60) return 'text-red-400';
  if (score >= 20) return 'text-red-300';
  if (score >= -20) return 'text-slate-400';
  if (score >= -60) return 'text-emerald-300';
  return 'text-emerald-400';
}

/** Tailwind text-colour class for a price/percentage change (red = up). */
export function changeTextClass(v: number): string {
  if (v > 0) return 'text-red-400';
  if (v < 0) return 'text-emerald-400';
  return 'text-slate-400';
}

/** Localised label + badge classes for an overall/dimension signal. */
export function signalMeta(signal: string | null | undefined): { label: string; cls: string } {
  switch (signal) {
    case 'strong_buy':
      return { label: '強力買進', cls: 'bg-red-500/15 text-red-400 border-red-500/30' };
    case 'buy':
    case 'bullish':
      return { label: '買進', cls: 'bg-red-500/10 text-red-300 border-red-500/25' };
    case 'sell':
    case 'bearish':
      return { label: '賣出', cls: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/25' };
    case 'strong_sell':
      return { label: '強力賣出', cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' };
    default:
      return { label: '中性', cls: 'bg-slate-500/15 text-slate-400 border-slate-600/40' };
  }
}
