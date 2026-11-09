import type { Broadcast, NotificationItem, TrafficSummary, TrafficWindow } from "../../types/operations.ts";

export type QuickAction = { key: string; label: string; target: string; enabled: boolean; reason: string | null };

export type HistoryRow = { label: string; shortLabel: string; startHour: number; percentage: number; isBusiest: boolean; isQuietest: boolean };

export type HistoryView =
  | { kind: "insufficient"; reason: string }
  | { kind: "ready"; busiest: TrafficWindow | null; quietest: TrafficWindow | null; rows: HistoryRow[] };

export const INSUFFICIENT_DATA_TITLE = "Not enough attendance data yet";
const DEFAULT_REASON = "This gym has not recorded enough visits last month to show a reliable pattern.";

/** Short axis label for a two-hour window, for example "6 PM". */
export function shortHourLabel(hour: number): string {
  const normalized = hour % 24;
  const suffix = normalized >= 12 ? "PM" : "AM";
  const twelve = normalized % 12 === 0 ? 12 : normalized % 12;
  return `${twelve} ${suffix}`;
}

/** Turns the traffic summary into what the page may show. Nothing is invented when data is insufficient. */
export function buildHistoryView(summary: TrafficSummary): HistoryView {
  if (!summary.data_sufficient) {
    return { kind: "insufficient", reason: summary.insufficiency_reason ?? DEFAULT_REASON };
  }
  const rows = [...summary.buckets]
    .sort((a, b) => a.start_hour - b.start_hour)
    .map((bucket) => ({
      label: bucket.label,
      shortLabel: shortHourLabel(bucket.start_hour),
      startHour: bucket.start_hour,
      percentage: bucket.average_capacity_percentage,
      isBusiest: summary.busiest_window?.start_hour === bucket.start_hour,
      isQuietest: summary.quietest_window?.start_hour === bucket.start_hour,
    }));
  return { kind: "ready", busiest: summary.busiest_window, quietest: summary.quietest_window, rows };
}

/** The QR code lives on the dashboard itself, so it is never offered as a quick action. */
export function visibleQuickActions(actions: QuickAction[]): QuickAction[] {
  return actions.filter((action) => action.key !== "qr");
}

/** A broadcast already shown as an announcement is not repeated in the notification list. */
export function dedupeNotifications(notifications: NotificationItem[], broadcasts: Broadcast[]): NotificationItem[] {
  const shown = new Set(broadcasts.map((item) => `${item.title}\n${item.message}`));
  return notifications.filter((item) => !shown.has(`${item.title}\n${item.message}`));
}

export function formatPercentage(value: number): string {
  return `${Math.round(value)}%`;
}
