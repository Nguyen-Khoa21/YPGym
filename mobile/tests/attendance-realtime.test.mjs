import assert from 'node:assert/strict';
import test from 'node:test';

import { attendanceCloseDisposition, attendanceRealtimeUrl, attendanceReconnectDelay, closeAttendanceSocket, isAttendanceQueryKey, isAttendanceRefreshMessage } from '../src/lib/attendance-realtime.ts';

test('creates the matching websocket URL', () => {
  assert.equal(attendanceRealtimeUrl('http://192.168.1.20:8001/api/v1/attendance/realtime'), 'ws://192.168.1.20:8001/api/v1/attendance/realtime');
  assert.equal(attendanceRealtimeUrl('https://api.example.test/api/v1/attendance/realtime'), 'wss://api.example.test/api/v1/attendance/realtime');
});

test('uses bounded jittered reconnect delays', () => {
  assert.equal(attendanceReconnectDelay(1, () => 0), 1500);
  assert.equal(attendanceReconnectDelay(20, () => 1), 30000);
});

test('recognizes refresh and heartbeat frames', () => {
  assert.equal(isAttendanceRefreshMessage({ type: 'occupancy_changed' }), true);
  assert.equal(isAttendanceRefreshMessage({ type: 'resync_required' }), true);
  assert.equal(isAttendanceRefreshMessage({ type: 'ping' }), false);
});

test('refreshes attendance, dashboard, QR and attendance-gated training queries', () => {
  for (const root of ['dashboard', 'attendance', 'qr', 'training']) assert.equal(isAttendanceQueryKey([root]), true);
  for (const root of ['memberships', 'classes', 'notifications']) assert.equal(isAttendanceQueryKey([root]), false);
});

test('unauthorized close logs out and background clients stay disconnected', () => {
  assert.equal(attendanceCloseDisposition(4401, true, false), 'logout');
  assert.equal(attendanceCloseDisposition(1006, true, false), 'reconnect');
  assert.equal(attendanceCloseDisposition(1006, false, false), 'stop');
  assert.equal(attendanceCloseDisposition(1006, true, true), 'stop');
});

test('logout and background cleanup close the active socket', () => {
  const calls = [];
  closeAttendanceSocket({ close: (...args) => calls.push(args) }, 'App backgrounded');
  assert.deepEqual(calls, [[1000, 'App backgrounded']]);
});
