import type {
  Broadcast,
  NotificationItem,
  TrafficSummary,
  TrafficWindow,
} from "../../types/operations.ts";

export type QuickAction = {
  key: string;
  label: string;
  target: string;
  enabled: boolean;
  reason: string | null;
};

export type HistoryRow = {
  label: string;
  shortLabel: string;
  startHour: number;
  percentage: number;
  isBusiest: boolean;
  isQuietest: boolean;
};

export type HistoryView =
  | { kind: "insufficient"; reason: string }
  | {
      kind: "ready";
      busiest: TrafficWindow | null;
      quietest: TrafficWindow | null;
      rows: HistoryRow[];
    };

export const INSUFFICIENT_DATA_TITLE = "Not enough attendance data yet";
const DEFAULT_REASON =
  "This gym has not recorded enough visits last month to show a reliable pattern.";

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
  return {
    kind: "ready",
    busiest: summary.busiest_window,
    quietest: summary.quietest_window,
    rows,
  };
}

/** The QR code lives on the dashboard itself, so it is never offered as a quick action. */
export function visibleQuickActions(actions: QuickAction[]): QuickAction[] {
  return actions.filter((action) => action.key !== "qr");
}

/** A broadcast already shown as an announcement is not repeated in the notification list. */
export function dedupeNotifications(
  notifications: NotificationItem[],
  broadcasts: Broadcast[],
): NotificationItem[] {
  const shown = new Set(broadcasts.map((item) => `${item.title}\n${item.message}`));
  return notifications.filter((item) => !shown.has(`${item.title}\n${item.message}`));
}

export function formatPercentage(value: number): string {
  return `${Math.round(value)}%`;
}

/** "District 1" and "YPGym District 1" both read as "YPGym District 1"; the prefix is never doubled. */
export function gymDisplayName(name: string | null | undefined): string | null {
  const trimmed = name?.trim();
  if (!trimmed) return null;
  return /^ypgym\b/i.test(trimmed) ? trimmed : `YPGym ${trimmed}`;
}

/** Heading of the occupancy history. Falls back to a plain word while no gym name is known. */
export function occupancyHeading(name: string | null | undefined): string {
  const display = gymDisplayName(name);
  return display ? `${display}'s Occupancy` : "Occupancy";
}

export type DashboardTab = "important" | "membership";
export type ImportantItem = {
  kind: "broadcast" | "notification";
  id: string;
  title: string;
  message: string;
};

/** Active broadcasts first, then unread notifications, each message once, at most `limit` items. */
export function importantItems(
  broadcasts: Broadcast[],
  notifications: NotificationItem[],
  limit = 5,
): ImportantItem[] {
  const unread = dedupeNotifications(notifications, broadcasts).filter(
    (item) => item.read_at === null,
  );
  return [
    ...broadcasts.map((item) => ({
      kind: "broadcast" as const,
      id: item.id,
      title: item.title,
      message: item.message,
    })),
    ...unread.map((item) => ({
      kind: "notification" as const,
      id: item.id,
      title: item.title,
      message: item.message,
    })),
  ].slice(0, limit);
}

/** Open on Important when there is something to read, otherwise on Membership. */
export function defaultDashboardTab(unreadCount: number, broadcastCount: number): DashboardTab {
  return unreadCount > 0 || broadcastCount > 0 ? "important" : "membership";
}

/** Unread badge text: nothing at 0 and "99+" above 99. */
export function formatBadgeCount(count: number): string {
  if (count <= 0) return "";
  return count > 99 ? "99+" : String(count);
}

/** Arrow-key navigation across tabs. Returns the index to focus, or null when the key is not a tab key. */
export function nextTabIndex(current: number, key: string, count: number): number | null {
  if (count <= 0) return null;
  if (key === "ArrowRight") return (current + 1) % count;
  if (key === "ArrowLeft") return (current - 1 + count) % count;
  if (key === "Home") return 0;
  if (key === "End") return count - 1;
  return null;
}
