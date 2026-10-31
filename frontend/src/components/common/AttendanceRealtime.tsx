import { useEffect } from "react";

import { useAuth } from "@/features/auth/AuthContext";
import { attendanceCloseDisposition, attendanceRealtimeUrl, attendanceReconnectDelay, closeAttendanceSocket, invalidateAttendanceQueries, isAttendanceRefreshMessage } from "@/lib/attendanceRealtime";
import { queryClient } from "@/lib/queryClient";

export function AttendanceRealtime() {
  const { token, user } = useAuth();

  useEffect(() => {
    if (!token || !user || !["member", "staff", "manager", "admin"].includes(user.role)) return;
    let socket: WebSocket | undefined;
    let retryTimer: number | undefined;
    let refreshTimer: number | undefined;
    let stopped = false;
    let attempts = 0;

    const connect = () => {
      if (stopped || document.visibilityState === "hidden") return;
      if (socket && socket.readyState < WebSocket.CLOSING) return;
      if (retryTimer) window.clearTimeout(retryTimer);
      retryTimer = undefined;
      socket = new WebSocket(attendanceRealtimeUrl());
      socket.addEventListener("open", () => {
        attempts = 0;
        socket?.send(JSON.stringify({ type: "authenticate", access_token: token }));
      });
      socket.addEventListener("message", (message) => {
        let payload: unknown;
        try { payload = JSON.parse(String(message.data)); } catch { return; }
        if ((payload as { type?: string })?.type === "ping") {
          socket?.send(JSON.stringify({ type: "pong" }));
        } else if (isAttendanceRefreshMessage(payload)) {
          if (refreshTimer) window.clearTimeout(refreshTimer);
          refreshTimer = window.setTimeout(() => void invalidateAttendanceQueries(queryClient), 50);
        }
      });
      socket.addEventListener("close", (event) => {
        socket = undefined;
        const disposition = attendanceCloseDisposition(event.code, document.visibilityState === "visible", stopped);
        if (disposition === "stop") return;
        if (disposition === "logout") {
          window.dispatchEvent(new Event("ypgym:unauthorized"));
          return;
        }
        attempts += 1;
        retryTimer = window.setTimeout(connect, attendanceReconnectDelay(attempts));
      });
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible" && (!socket || socket.readyState >= WebSocket.CLOSING)) connect();
      if (document.visibilityState === "hidden") closeAttendanceSocket(socket, "Page hidden");
    };
    document.addEventListener("visibilitychange", onVisibility);
    connect();
    return () => {
      stopped = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      if (refreshTimer) window.clearTimeout(refreshTimer);
      document.removeEventListener("visibilitychange", onVisibility);
      closeAttendanceSocket(socket, "Client closed");
    };
  }, [token, user]);

  return null;
}
