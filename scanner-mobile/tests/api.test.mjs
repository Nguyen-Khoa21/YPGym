import assert from 'node:assert/strict';
import test from 'node:test';

import { ScannerApiError, submitScan, verifyDevice } from '../src/api.ts';

const credentials = { apiBaseUrl: 'https://api.example.test/api/v1', deviceId: 'door-1', apiKey: 'secret-device-key-not-logged', mode: 'both' };

test('device verification and explicit scan action use the device contract', async () => {
  const calls = [];
  const fetcher = async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify(url.endsWith('/verify') ? { device_id: 'door-1', display_name: 'Front door', status: 'active' } : {
      code: 'CHECK_IN_SUCCESS', message: 'Check-in recorded.', session_id: 'session', member_id: 'member', member: { display_name: 'Test Member', membership_status: 'active' }, attendance_status: 'active', action: 'check_in', occurred_at: new Date().toISOString(), occupancy: { active_count: 1, capacity: 10, percentage: 10, status: 'Low', calculated_at: new Date().toISOString() },
    }), { status: 200, headers: { 'content-type': 'application/json' } });
  };
  await verifyDevice(credentials, fetcher);
  const result = await submitScan(credentials, 'check_in', 'q'.repeat(30), fetcher);
  assert.equal(result.member.display_name, 'Test Member');
  assert.equal(calls[1].url.endsWith('/attendance/check-in'), true);
  assert.equal(JSON.parse(calls[1].init.body).qr_token.length, 30);
});

test('check-out mode uses the explicit check-out endpoint', async () => {
  let calledUrl = '';
  const fetcher = async (url) => {
    calledUrl = url;
    return new Response(JSON.stringify({
      code: 'CHECK_OUT_SUCCESS', message: 'Check-out recorded.', session_id: 'session', member_id: 'member', member: { display_name: 'Test Member', membership_status: 'active' }, attendance_status: 'checked_out', action: 'check_out', occurred_at: '2026-10-27T02:00:00Z', occupancy: { active_count: 0, capacity: 10, percentage: 0, status: 'Low', calculated_at: '2026-10-27T02:00:00Z' },
    }), { status: 200, headers: { 'content-type': 'application/json' } });
  };
  const result = await submitScan(credentials, 'check_out', 'q'.repeat(30), fetcher);
  assert.equal(calledUrl.endsWith('/attendance/check-out'), true);
  assert.equal(result.attendance_status, 'checked_out');
});

test('network and API errors never claim success and retain request ID', async () => {
  await assert.rejects(() => submitScan(credentials, 'check_out', 'q'.repeat(30), async () => { throw new Error('offline'); }), (error) => error instanceof ScannerApiError && error.code === 'NETWORK_ERROR');
  const failed = async () => new Response(JSON.stringify({ error: { code: 'EXPIRED_TOKEN', message: 'Expired.' } }), { status: 400, headers: { 'x-request-id': 'request-123' } });
  await assert.rejects(() => submitScan(credentials, 'check_out', 'q'.repeat(30), failed), (error) => error.code === 'EXPIRED_TOKEN' && error.requestId === 'request-123');
});
