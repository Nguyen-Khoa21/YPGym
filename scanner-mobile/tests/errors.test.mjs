import assert from 'node:assert/strict';
import test from 'node:test';

import { isDeviceBlocked, isNetworkError, staffGuidance } from '../src/errors.ts';

const codes = ['INVALID_DEVICE', 'INVALID_TOKEN', 'EXPIRED_TOKEN', 'SUPERSEDED_TOKEN', 'INACTIVE_MEMBERSHIP', 'DUPLICATE_SCAN', 'ACTIVE_SESSION_EXISTS', 'NO_ACTIVE_SESSION', 'QR_STATE_UNAVAILABLE', 'SCAN_STATE_UNAVAILABLE', 'VALIDATION_ERROR', 'INTERNAL_SERVER_ERROR'];

test('every stable scanner code has safe guidance', () => {
  for (const code of codes) assert.ok(staffGuidance({ code, message: code === 'INACTIVE_MEMBERSHIP' ? 'Membership is frozen.' : '' }).length > 10);
  assert.equal(isDeviceBlocked('INVALID_DEVICE'), true);
  assert.equal(isNetworkError('NETWORK_ERROR'), true);
  assert.match(staffGuidance({ code: 'UNKNOWN', message: 'raw server body' }), /could not be completed/);
});
