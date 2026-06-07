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
