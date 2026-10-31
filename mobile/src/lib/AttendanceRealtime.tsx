import { useEffect } from 'react';
import { AppState } from 'react-native';

import { attendanceCloseDisposition, attendanceRealtimeUrl, attendanceReconnectDelay, closeAttendanceSocket, invalidateAttendanceQueries, isAttendanceRefreshMessage } from '@/lib/attendance-realtime';
import { useAuth } from '@/lib/auth';
import { queryClient } from '@/lib/query';

export function AttendanceRealtime() {
  const { token, user, logout } = useAuth();

  useEffect(() => {
    const url = attendanceRealtimeUrl();
    if (!url || !token || user?.role !== 'member') return;
    let socket: WebSocket | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let refreshTimer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;
    let attempts = 0;
    const connect = () => {
      if (stopped || AppState.currentState !== 'active') return;
      if (socket && socket.readyState < WebSocket.CLOSING) return;
      if (timer) clearTimeout(timer);
      timer = undefined;
      socket = new WebSocket(url);
      socket.onopen = () => {
        attempts = 0;
        socket?.send(JSON.stringify({ type: 'authenticate', access_token: token }));
      };
      socket.onmessage = (message) => {
        let payload: unknown;
        try { payload = JSON.parse(String(message.data)); } catch { return; }
        if ((payload as { type?: string })?.type === 'ping') socket?.send(JSON.stringify({ type: 'pong' }));
        else if (isAttendanceRefreshMessage(payload)) {
          if (refreshTimer) clearTimeout(refreshTimer);
          refreshTimer = setTimeout(() => void invalidateAttendanceQueries(queryClient), 50);
        }
      };
      socket.onclose = (event) => {
        socket = undefined;
        const disposition = attendanceCloseDisposition(event.code, AppState.currentState === 'active', stopped);
        if (disposition === 'stop') return;
        if (disposition === 'logout') { void logout(); return; }
        attempts += 1;
        timer = setTimeout(connect, attendanceReconnectDelay(attempts));
      };
    };
    const subscription = AppState.addEventListener('change', (state) => {
      if (state === 'active' && (!socket || socket.readyState >= WebSocket.CLOSING)) connect();
      if (state !== 'active') {
        if (timer) clearTimeout(timer);
        closeAttendanceSocket(socket, 'App backgrounded');
      }
    });
    connect();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      if (refreshTimer) clearTimeout(refreshTimer);
      subscription.remove();
      closeAttendanceSocket(socket, 'Client closed');
    };
  }, [logout, token, user]);

  return null;
}
