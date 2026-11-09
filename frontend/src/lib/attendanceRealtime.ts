import type { QueryClient } from "@tanstack/react-query";

import { matchesEventGym } from "../features/operations/gymScope.ts";
import { API_BASE_URL } from "./apiClient.ts";

const attendanceRoots = new Set([
  "dashboard",
  "attendance",
  "training",
]);

export type AttendanceCloseDisposition = "stop" | "logout" | "reconnect";

export function attendanceRealtimeUrl(apiBaseUrl = API_BASE_URL) {
  const url = new URL(`${apiBaseUrl.replace(/\/$/, "")}/attendance/realtime`);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

/** Refresh attendance queries. With an event gym, queries marked for another gym are left alone. */
export function invalidateAttendanceQueries(client: QueryClient, eventGymId?: string | null) {
  return client.invalidateQueries({
    predicate: (query) => isAttendanceQueryKey(query.queryKey) && matchesEventGym(query.queryKey, eventGymId),
    refetchType: "active",
  });
}

export function isAttendanceQueryKey(queryKey: readonly unknown[]) {
  return attendanceRoots.has(String(queryKey[0]));
}

export function isAttendanceRefreshMessage(value: unknown) {
  if (!value || typeof value !== "object") return false;
  const type = (value as { type?: unknown }).type;
  return type === "attendance_changed" || type === "occupancy_changed" || type === "resync_required";
}

export function attendanceEventGymId(value: unknown): string | null {
  const gymId = (value as { gym_id?: unknown } | null)?.gym_id;
  return typeof gymId === "string" ? gymId : null;
}

/** First frame sent after the socket opens. The owner may scope it to one gym; the server enforces everyone else's. */
export function attendanceAuthFrame(accessToken: string, gymId?: string | null) {
  return { type: "authenticate", access_token: accessToken, ...(gymId ? { gym_id: gymId } : {}) };
}

export function attendanceReconnectDelay(attempt: number, random = Math.random) {
  const ceiling = Math.min(1000 * 2 ** attempt, 30_000);
  return Math.min(30_000, Math.floor(ceiling * (0.75 + random() * 0.5)));
}

export function attendanceCloseDisposition(code: number, active: boolean, stopped: boolean): AttendanceCloseDisposition {
  if (stopped || !active) return "stop";
  return code === 4401 ? "logout" : "reconnect";
}

export function closeAttendanceSocket(socket: Pick<WebSocket, "close"> | undefined, reason: string) {
  socket?.close(1000, reason);
}
