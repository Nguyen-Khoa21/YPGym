import assert from 'node:assert/strict';
import test from 'node:test';

import { mayShowQr, qrSecondsLeft } from '../src/lib/qr.ts';

test('expired or malformed QR material is never displayed', () => {
  const expiry = '2026-09-13T12:00:05.000Z';
  assert.equal(qrSecondsLeft(expiry, Date.parse('2026-09-13T12:00:00.000Z')), 5);
  assert.equal(qrSecondsLeft(expiry, Date.parse(expiry)), 0);
  assert.equal(qrSecondsLeft('invalid', Date.now()), 0);
  assert.equal(mayShowQr(true, true, false, 0, true), false);
  assert.equal(mayShowQr(true, true, false, 5, true), true);
});

test('background, failed refresh, or ineligible membership hides an otherwise valid code', () => {
  assert.equal(mayShowQr(true, false, false, 20, true), false);
  assert.equal(mayShowQr(true, true, true, 20, true), false);
  assert.equal(mayShowQr(false, true, false, 20, true), false);
  assert.equal(mayShowQr(true, true, false, 20, false), false);
});
