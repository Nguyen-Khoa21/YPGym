import assert from "node:assert/strict";
import test from "node:test";

import { buildHistoryView, dedupeNotifications, shortHourLabel, visibleQuickActions } from "../src/features/member/memberDashboardLogic.ts";

const window = (start, pct) => ({ start_hour: start, end_hour: start + 2, label: `${start}-${start + 2}`, average_headcount: pct, average_capacity_percentage: pct, sample_count: 4 });
const summary = (overrides = {}) => ({
  data_sufficient: true,
  insufficiency_reason: null,
  busiest_window: window(18, 80),
  quietest_window: window(2, 3),
  buckets: Array.from({ length: 12 }, (_, i) => window(22 - i * 2, i * 7)),
  ...overrides,
});

test("history rows are ordered by window start and keep each percentage", () => {
  const view = buildHistoryView(summary());
  assert.equal(view.kind, "ready");
  assert.equal(view.rows.length, 12);
  assert.deepEqual(view.rows.map((row) => row.startHour), [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]);
  assert.equal(view.rows[0].percentage, 77);
  assert.equal(view.rows.find((row) => row.startHour === 18).isBusiest, true);
  assert.equal(view.rows.find((row) => row.startHour === 2).isQuietest, true);
});

test("insufficient data produces no windows and no rows", () => {
  const view = buildHistoryView(summary({ data_sufficient: false, insufficiency_reason: "Fewer than 20 sessions.", buckets: [], busiest_window: null, quietest_window: null }));
  assert.deepEqual(view, { kind: "insufficient", reason: "Fewer than 20 sessions." });
  assert.equal(buildHistoryView(summary({ data_sufficient: false })).kind, "insufficient");
  assert.ok(buildHistoryView(summary({ data_sufficient: false })).reason.length > 0);
});

test("the QR code is not a quick action", () => {
  const actions = [
    { key: "membership", label: "Buy membership", target: "/memberships", enabled: true, reason: null },
    { key: "qr", label: "QR code", target: "/app/qr", enabled: true, reason: null },
    { key: "classes", label: "Classes", target: "/app/classes", enabled: true, reason: null },
  ];
  assert.deepEqual(visibleQuickActions(actions).map((action) => action.key), ["membership", "classes"]);
});

test("a broadcast is not repeated in the notification list", () => {
  const notifications = [{ id: "1", title: "Closed Friday", message: "Holiday" }, { id: "2", title: "Booked", message: "Yoga" }];
  const broadcasts = [{ id: "b", title: "Closed Friday", message: "Holiday" }];
  assert.deepEqual(dedupeNotifications(notifications, broadcasts).map((item) => item.id), ["2"]);
});

test("window labels read as clock times", () => {
  assert.equal(shortHourLabel(0), "12 AM");
  assert.equal(shortHourLabel(12), "12 PM");
  assert.equal(shortHourLabel(18), "6 PM");
});
