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

const { defaultDashboardTab, formatBadgeCount, gymDisplayName, importantItems, nextTabIndex, occupancyHeading } = await import("../src/features/member/memberDashboardLogic.ts");

test("the occupancy heading never doubles the YPGym prefix", () => {
  assert.equal(occupancyHeading("YPGym District 11"), "YPGym District 11's Occupancy");
  assert.equal(occupancyHeading("District 1"), "YPGym District 1's Occupancy");
  assert.equal(occupancyHeading("ypgym District 1"), "ypgym District 1's Occupancy");
  assert.equal(occupancyHeading(null), "Occupancy");
  assert.equal(occupancyHeading("  "), "Occupancy");
  assert.equal(gymDisplayName("YPGym District 1"), "YPGym District 1");
});

test("important items list broadcasts first, then unread notifications, each once and at most five", () => {
  const broadcasts = [{ id: "b1", title: "Closed Friday", message: "Holiday" }];
  const notifications = [
    { id: "n1", title: "Closed Friday", message: "Holiday", read_at: null },
    { id: "n2", title: "Booked", message: "Yoga", read_at: null },
    { id: "n3", title: "Old", message: "Read already", read_at: "2026-01-01T00:00:00Z" },
  ];
  assert.deepEqual(importantItems(broadcasts, notifications).map((item) => item.id), ["b1", "n2"]);
  const many = Array.from({ length: 9 }, (_, index) => ({ id: `n${index}`, title: `T${index}`, message: "m", read_at: null }));
  assert.equal(importantItems(broadcasts, many).length, 5);
  assert.deepEqual(importantItems([], []), []);
});

test("the default tab is Important only when there is something to read", () => {
  assert.equal(defaultDashboardTab(0, 0), "membership");
  assert.equal(defaultDashboardTab(2, 0), "important");
  assert.equal(defaultDashboardTab(0, 1), "important");
});

test("badge counts hide at zero and cap at 99+", () => {
  assert.equal(formatBadgeCount(0), "");
  assert.equal(formatBadgeCount(3), "3");
  assert.equal(formatBadgeCount(99), "99");
  assert.equal(formatBadgeCount(120), "99+");
});

test("arrow keys move between tabs and wrap", () => {
  assert.equal(nextTabIndex(0, "ArrowRight", 2), 1);
  assert.equal(nextTabIndex(1, "ArrowRight", 2), 0);
  assert.equal(nextTabIndex(0, "ArrowLeft", 2), 1);
  assert.equal(nextTabIndex(1, "Home", 2), 0);
  assert.equal(nextTabIndex(0, "End", 2), 1);
  assert.equal(nextTabIndex(0, "a", 2), null);
});
