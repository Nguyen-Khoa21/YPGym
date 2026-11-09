import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import type { Crowdedness, QrToken, TrafficSummary } from "@/types/operations";

/**
 * Rotating attendance QR token. The token is held only in query memory, is refetched five seconds
 * before it expires and again when the window regains focus. Pass enabled=false to make no request.
 */
export function useRotatingQr(enabled = true) {
  const { token } = useAuth();
  const query = useQuery({
    queryKey: ["attendance", "qr-token"],
    queryFn: ({ signal }) => apiRequest<QrToken>("/attendance/qr-token/me", { token, signal }),
    enabled,
    retry: false,
    refetchOnWindowFocus: true,
  });
  const expiresAt = query.data?.expires_at;
  const refetch = query.refetch;
  const secondsLeft = useSecondsLeft(expiresAt);

  useEffect(() => {
    if (!expiresAt) return;
    const refreshIn = Math.max(1_000, new Date(expiresAt).getTime() - Date.now() - 5_000);
    const timer = window.setTimeout(() => { void refetch(); }, refreshIn);
    return () => window.clearTimeout(timer);
  }, [expiresAt, refetch]);

  return { query, secondsLeft };
}

/** Last month's two-hour pattern for the signed-in member's own gym. The server chooses the gym. */
export function useTrafficSummary(enabled = true) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["attendance", "traffic-summary", "me"],
    queryFn: ({ signal }) => apiRequest<TrafficSummary>("/attendance/traffic-summary", { token, signal }),
    enabled,
    staleTime: 300_000,
  });
}

/** Live occupancy of the member's own gym. */
export function useHomeCrowdedness(enabled = true) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["attendance", "crowdedness"],
    queryFn: ({ signal }) => apiRequest<Crowdedness>("/attendance/crowdedness", { token, signal }),
    enabled,
    refetchInterval: 30_000,
  });
}

function useSecondsLeft(expiresAt?: string) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1_000);
    return () => window.clearInterval(timer);
  }, []);
  if (!expiresAt) return 0;
  return Math.max(0, Math.ceil((new Date(expiresAt).getTime() - now) / 1_000));
}
