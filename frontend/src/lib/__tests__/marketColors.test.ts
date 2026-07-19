import { describe, it, expect } from 'vitest';
import {
  scoreHex,
  scoreTextClass,
  changeTextClass,
  signalMeta,
  UP_HEX,
  DOWN_HEX,
} from '../marketColors';

// Taiwan convention: red = up/bullish, green = down/bearish.
describe('marketColors (紅漲綠跌)', () => {
  it('high score maps to red, low to green', () => {
    expect(scoreHex(80)).toBe(UP_HEX);
    expect(scoreHex(-80)).toBe(DOWN_HEX);
  });

  it('neutral band is gray', () => {
    expect(scoreTextClass(0)).toContain('slate');
    expect(scoreTextClass(19)).toContain('slate');
  });

  it('positive change is red text, negative is emerald', () => {
    expect(changeTextClass(1.5)).toContain('red');
    expect(changeTextClass(-1.5)).toContain('emerald');
    expect(changeTextClass(0)).toContain('slate');
  });

  it('signalMeta localises all signals', () => {
    expect(signalMeta('strong_buy').label).toBe('強力買進');
    expect(signalMeta('buy').label).toBe('買進');
    expect(signalMeta('sell').label).toBe('賣出');
    expect(signalMeta('strong_sell').label).toBe('強力賣出');
    expect(signalMeta('neutral').label).toBe('中性');
    expect(signalMeta(null).label).toBe('中性');
  });

  it('buy signals use red classes, sell signals use emerald', () => {
    expect(signalMeta('strong_buy').cls).toContain('red');
    expect(signalMeta('strong_sell').cls).toContain('emerald');
  });
});
