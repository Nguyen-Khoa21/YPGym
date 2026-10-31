import type { QueryClient } from '@tanstack/react-query';

const roots = new Set(['dashboard', 'attendance', 'qr', 'training']);

export type AttendanceCloseDisposition = 'stop' | 'logout' | 'reconnect';

const configuredBaseUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '');

export function attendanceRealtimeUrl(httpUrl = configuredBaseUrl ? `${configuredBaseUrl}/attendance/realtime` : '') {
  if (!httpUrl) return '';
  return httpUrl.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
}

export function isAttendanceRefreshMessage(value: unknown) {
  if (!value || typeof value !== 'object') return false;
  const type = (value as { type?: unknown }).type;
  return type === 'attendance_changed' || type === 'occupancy_changed' || type === 'resync_required';
}

export function attendanceReconnectDelay(attempt: number, random = Math.random) {
  const ceiling = Math.min(1000 * 2 ** attempt, 30_000);
  return Math.min(30_000, Math.floor(ceiling * (0.75 + random() * 0.5)));
}

export function invalidateAttendanceQueries(client: QueryClient) {
  return client.invalidateQueries({ predicate: (query) => isAttendanceQueryKey(query.queryKey), refetchType: 'active' });
}

export function isAttendanceQueryKey(queryKey: readonly unknown[]) {
  return roots.has(String(queryKey[0]));
}

export function attendanceCloseDisposition(code: number, active: boolean, stopped: boolean): AttendanceCloseDisposition {
  if (stopped || !active) return 'stop';
  return code === 4401 ? 'logout' : 'reconnect';
}

export function closeAttendanceSocket(socket: Pick<WebSocket, 'close'> | undefined, reason: string) {
  socket?.close(1000, reason);
}
