import { useEffect, useSyncExternalStore } from "react";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import type { GymLocation } from "@/types/operations";
import { effectiveOwnerGym, gymSelectionStore, realtimeGymStore } from "./gymScope";

/**
 * The gym scope of the current operations page.
 * Owner: a selectable branch, or all branches. Manager and staff: their one assigned gym, from GET /gyms/me.
 */
export function useOperationsScope() {
  const { token, user } = useAuth();
  const isOwner = user?.role === "admin";
  const selection = useSyncExternalStore(gymSelectionStore.subscribe, gymSelectionStore.get);
  const gyms = useQuery({
    queryKey: ["gyms", "active"],
    queryFn: ({ signal }) => apiRequest<GymLocation[]>("/gyms", { signal }),
    enabled: isOwner,
    staleTime: 300_000,
  });
  const mine = useQuery({
    queryKey: ["gyms", "me", user?.id],
    queryFn: ({ signal }) => apiRequest<GymLocation>("/gyms/me", { token, signal }),
    enabled: Boolean(user) && !isOwner,
    staleTime: 300_000,
  });

  const gymId = isOwner ? effectiveOwnerGym(selection, gyms.data?.[0]?.id) : mine.data?.id ?? "";
  const gymName = isOwner
    ? gymId ? gyms.data?.find((gym) => gym.id === gymId)?.name ?? "Selected branch" : "All branches"
    : mine.data?.name;
  const ready = isOwner ? gyms.isSuccess : mine.isSuccess;

  // The realtime socket follows the owner's branch. Staff and managers are fixed by the server.
  useEffect(() => {
    if (!isOwner || !ready) return;
    realtimeGymStore.set(gymId || null);
    return () => realtimeGymStore.set(null);
  }, [isOwner, ready, gymId]);

  return {
    isOwner,
    ready,
    gymId,
    gymName,
    gyms: gyms.data ?? [],
    /** The gym_id to send to the API. Only the owner names a gym; for everyone else the server decides. */
    gymParam: isOwner ? gymId : "",
    error: isOwner ? gyms.error : mine.error,
    retry: () => void (isOwner ? gyms.refetch() : mine.refetch()),
    selectGym: (value: string) => gymSelectionStore.set(value),
  };
}

export type OperationsScope = ReturnType<typeof useOperationsScope>;
