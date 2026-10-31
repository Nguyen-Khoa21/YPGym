import assert from "node:assert/strict";
import test from "node:test";

import { attendanceCloseDisposition, attendanceRealtimeUrl, attendanceReconnectDelay, closeAttendanceSocket, isAttendanceQueryKey, isAttendanceRefreshMessage } from "../src/lib/attendanceRealtime.ts";

test("builds secure and local realtime URLs", () => {
  assert.equal(attendanceRealtimeUrl("http://localhost:8001/api/v1"), "ws://localhost:8001/api/v1/attendance/realtime");
  assert.equal(attendanceRealtimeUrl("https://api.example.test/api/v1"), "wss://api.example.test/api/v1/attendance/realtime");
});

test("reconnect delay is bounded and jittered", () => {
  assert.equal(attendanceReconnectDelay(1, () => 0), 1500);
  assert.equal(attendanceReconnectDelay(20, () => 1), 30000);
});

test("only attendance invalidation messages trigger a refresh", () => {
  assert.equal(isAttendanceRefreshMessage({ type: "attendance_changed" }), true);
  assert.equal(isAttendanceRefreshMessage({ type: "resync_required" }), true);
  assert.equal(isAttendanceRefreshMessage({ type: "ping" }), false);
  assert.equal(isAttendanceRefreshMessage(null), false);
});

test("refreshes every authoritative attendance consumer and not unrelated data", () => {
  for (const root of ["dashboard", "attendance", "training"]) assert.equal(isAttendanceQueryKey([root]), true);
  for (const root of ["memberships", "classes", "notifications", "admin"]) assert.equal(isAttendanceQueryKey([root]), false);
});

test("unauthorized close logs out, while hidden/stopped clients do not reconnect", () => {
  assert.equal(attendanceCloseDisposition(4401, true, false), "logout");
  assert.equal(attendanceCloseDisposition(1006, true, false), "reconnect");
  assert.equal(attendanceCloseDisposition(1006, false, false), "stop");
  assert.equal(attendanceCloseDisposition(1006, true, true), "stop");
});

test("logout and visibility cleanup close the active socket", () => {
  const calls = [];
  closeAttendanceSocket({ close: (...args) => calls.push(args) }, "Client closed");
  assert.deepEqual(calls, [[1000, "Client closed"]]);
});
