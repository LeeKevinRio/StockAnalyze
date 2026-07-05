/** Browser-stored user preferences (no backend). */

export const CHART_DAYS_KEY = 'pref_chart_days';
export const CHART_DAYS_OPTIONS = [60, 120, 250] as const;
export const DEFAULT_CHART_DAYS = 120;

export function getChartDays(): number {
  if (typeof window === 'undefined') return DEFAULT_CHART_DAYS;
  const v = Number(localStorage.getItem(CHART_DAYS_KEY));
  return (CHART_DAYS_OPTIONS as readonly number[]).includes(v) ? v : DEFAULT_CHART_DAYS;
}

export function setChartDays(days: number): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(CHART_DAYS_KEY, String(days));
}
