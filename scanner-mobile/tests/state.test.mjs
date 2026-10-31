import assert from 'node:assert/strict';
import test from 'node:test';

import { initialState, isQrPayloadLengthAllowed, scannerReducer, shouldAcceptScan, shouldRenderCamera } from '../src/state.ts';
import { initialActionForMode, parseCredentials, serializeCredentials } from '../src/credentials.ts';
import { createCredentialStore } from '../src/credential-store.ts';
import { buildSuccessPresentation } from '../src/presentation.ts';

const result = {
  code: 'CHECK_IN_SUCCESS', message: 'Check-in recorded.', session_id: 'session', member_id: 'member',
  member: { display_name: 'Nguyen Anh Khoa', membership_status: 'active' }, attendance_status: 'active', action: 'check_in',
  occurred_at: '2026-10-27T02:00:00Z', occupancy: { active_count: 24, capacity: 150, percentage: 16, status: 'Low', calculated_at: '2026-10-27T02:00:00Z' },
};

test('scanner accepts one bounded QR only while ready', () => {
  assert.equal(shouldAcceptScan('ready', false), true);
  assert.equal(shouldAcceptScan('ready', true), false);
  assert.equal(shouldAcceptScan('submitting', false), false);
  assert.equal(isQrPayloadLengthAllowed(20), true);
  assert.equal(isQrPayloadLengthAllowed(4097), false);
});

test('scanner state rejects invalid transitions and clears result on reset', () => {
  assert.deepEqual(scannerReducer(initialState, { type: 'SUBMIT' }), initialState);
  const ready = scannerReducer(initialState, { type: 'READY' });
  const detected = scannerReducer(ready, { type: 'CODE_DETECTED' });
  const submitting = scannerReducer(detected, { type: 'SUBMIT' });
  assert.equal(submitting.status, 'submitting');
  assert.equal(scannerReducer(submitting, { type: 'READY' }).status, 'submitting');
  const success = scannerReducer(submitting, { type: 'SUCCESS', result });
  assert.equal(success.status, 'success');
  const reset = scannerReducer(success, { type: 'READY' });
  assert.deepEqual(reset, { status: 'ready' });
  assert.equal('result' in reset, false);
});

test('stored provisioning must contain every required field', () => {
  const credentials = { apiBaseUrl: 'https://api.example.test/api/v1', deviceId: 'door-1', apiKey: 'x'.repeat(24), mode: 'both' };
  const stored = serializeCredentials(credentials);
  assert.deepEqual(parseCredentials(stored), credentials);
  assert.equal(stored.includes('qr_token'), false);
  assert.equal(parseCredentials('{"deviceId":"door-1"}'), null);
  assert.equal(parseCredentials('invalid'), null);
});

test('provisioned scanner modes choose only an explicit initial action', () => {
  assert.equal(initialActionForMode('both'), 'check_in');
  assert.equal(initialActionForMode('check_in'), 'check_in');
  assert.equal(initialActionForMode('check_out'), 'check_out');
});

test('provisioning is restored from and removed from the secure storage boundary', async () => {
  const values = new Map();
  const adapter = {
    async getItemAsync(key) { return values.get(key) ?? null; },
    async setItemAsync(key, value) { values.set(key, value); },
    async deleteItemAsync(key) { values.delete(key); },
  };
  const store = createCredentialStore(adapter);
  const credentials = { apiBaseUrl: 'https://api.example.test/api/v1', deviceId: 'door-1', apiKey: 'x'.repeat(24), mode: 'check_in' };
  assert.equal(await store.load(), null);
  await store.save(credentials);
  assert.deepEqual(await store.load(), credentials);
  assert.equal([...values.values()].some((value) => value.includes('qr_token')), false);
  await store.clear();
  assert.equal(await store.load(), null);
});

test('camera permission and foreground state control camera availability', () => {
  const permission = scannerReducer({ status: 'ready' }, { type: 'PERMISSION_REQUIRED' });
  assert.equal(permission.status, 'camera_permission_required');
  assert.equal(shouldRenderCamera(true, true, 'ready'), true);
  assert.equal(shouldRenderCamera(false, true, 'ready'), false);
  assert.equal(shouldRenderCamera(true, false, 'ready'), false);
  assert.equal(shouldRenderCamera(true, true, 'submitting'), false);
});

test('offline and blocked transitions never contain a queued QR', () => {
  const offline = scannerReducer({ status: 'submitting' }, { type: 'OFFLINE', error: { code: 'NETWORK_ERROR', message: 'offline' } });
  const blocked = scannerReducer({ status: 'ready' }, { type: 'DEVICE_BLOCKED', error: { code: 'INVALID_DEVICE', message: 'blocked' } });
  assert.equal(offline.status, 'offline');
  assert.equal(blocked.status, 'device_blocked');
  assert.equal('qrToken' in offline, false);
  assert.equal('qrToken' in blocked, false);
});

test('success presentation contains only the safe door result', () => {
  const presentation = buildSuccessPresentation(result, 'Asia/Ho_Chi_Minh');
  assert.equal(presentation.action, 'CHECKED IN');
  assert.equal(presentation.displayName, 'Nguyen Anh Khoa');
  assert.equal(presentation.membershipStatus, 'ACTIVE');
  assert.equal(presentation.occupancy, '24 / 150');
  assert.equal(presentation.crowdedness, 'Low occupancy');
  assert.deepEqual(Object.keys(presentation).sort(), ['action', 'crowdedness', 'displayName', 'membershipStatus', 'occupancy', 'occurredAt']);
});
