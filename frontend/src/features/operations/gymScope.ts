/**
 * Which gym an operations page is looking at.
 *
 * Staff and managers have one assigned gym that the server enforces. The owner picks a branch,
 * or "All branches". The selection lives in memory so every page and the realtime socket agree.
 * This file has no React imports so the rules can be tested with node --test.
 */

export type GymSelection = string | null;

/** Query keys for gym-specific data carry this marker so a realtime event can refresh only its own gym. */
export function gymMarker(gymId: string) {
  return { gymId } as const;
}

export function gymIdFromQueryKey(queryKey: readonly unknown[]): string | null {
  for (const part of queryKey) {
    if (part && typeof part === "object" && "gymId" in part) {
      const value = (part as { gymId?: unknown }).gymId;
      return typeof value === "string" ? value : null;
    }
  }
  return null;
}

/** A query without a gym marker is gym-independent and always refreshes. A marked query refreshes only for its gym. */
export function matchesEventGym(queryKey: readonly unknown[], eventGymId?: string | null): boolean {
  if (!eventGymId) return true;
  const own = gymIdFromQueryKey(queryKey);
  return own === null || own === eventGymId;
}

/** Owner default: the first branch. null means "not chosen yet", an empty string means "All branches". */
export function effectiveOwnerGym(selection: GymSelection, firstGymId?: string): string {
  return selection ?? firstGymId ?? "";
}

type Listener = () => void;

function createStore<T>(initial: T) {
  let value = initial;
  const listeners = new Set<Listener>();
  return {
    get: () => value,
    set(next: T) {
      if (Object.is(next, value)) return;
      value = next;
      listeners.forEach((listener) => listener());
    },
    subscribe(listener: Listener) {
      listeners.add(listener);
      return () => { listeners.delete(listener); };
    },
  };
}

/** The owner's branch choice. */
export const gymSelectionStore = createStore<GymSelection>(null);

/** The gym the page currently on screen is scoped to, for the realtime socket. null means every gym or not an operations page. */
export const realtimeGymStore = createStore<string | null>(null);

export function resetGymScope() {
  gymSelectionStore.set(null);
  realtimeGymStore.set(null);
}
