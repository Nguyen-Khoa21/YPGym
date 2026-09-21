import assert from 'node:assert/strict';
import test from 'node:test';

import { colors } from '../src/lib/theme.ts';

function luminance(hex) {
  const channels = hex.slice(1).match(/.{2}/g).map((value) => Number.parseInt(value, 16) / 255);
  const [red, green, blue] = channels.map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrast(first, second) {
  const brightest = Math.max(luminance(first), luminance(second));
  const darkest = Math.min(luminance(first), luminance(second));
  return (brightest + 0.05) / (darkest + 0.05);
}

test('workout theme uses a white surface and accessible semantic text colors', () => {
  assert.equal(colors.background, '#FFFFFF');
  assert.ok(contrast(colors.primary, colors.white) >= 4.5, 'primary actions need readable white labels');
  assert.ok(contrast(colors.text, colors.background) >= 7, 'body text needs strong contrast');
  assert.ok(contrast(colors.muted, colors.background) >= 4.5, 'muted copy still needs normal-text contrast');
  assert.ok(contrast(colors.danger, colors.dangerSurface) >= 4.5, 'error status needs readable text');
});
