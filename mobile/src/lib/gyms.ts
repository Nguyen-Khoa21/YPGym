import type { GymLocation } from './types';

// Adds ?gym_id= or &gym_id= to a path. Without a gym the path is returned unchanged,
// so the backend falls back to the member's previous home gym.
export function withGymParam(path: string, gymId: string | null | undefined) {
  if (!gymId) return path;
  return `${path}${path.includes('?') ? '&' : '?'}gym_id=${encodeURIComponent(gymId)}`;
}

export function activeGyms(gyms: GymLocation[] | undefined) {
  return (gyms ?? []).filter((gym) => gym.is_active);
}

export function gymNameFor(gyms: GymLocation[] | undefined, gymId: string | null | undefined) {
  return gymId ? gyms?.find((gym) => gym.id === gymId)?.name ?? null : null;
}

// The gym a renewal will be bought for: the member's pick if it is still active,
// otherwise their previous home gym if it is still active, otherwise nothing.
// A first-time member has no previous gym, so they must pick one.
// When the gym list could not be loaded the pick or home gym is passed through and the backend decides.
export function renewalGymId(gyms: GymLocation[] | undefined, picked: string | null, homeGymId: string | null | undefined) {
  if (!gyms) return picked ?? homeGymId ?? null;
  const active = activeGyms(gyms);
  if (picked && active.some((gym) => gym.id === picked)) return picked;
  if (homeGymId && active.some((gym) => gym.id === homeGymId)) return homeGymId;
  return null;
}

export function attendanceBenefitPath(planId: string, gymId: string | null | undefined) {
  return withGymParam(`/memberships/attendance-benefit/me?plan_id=${encodeURIComponent(planId)}`, gymId);
}

export function renewalCheckoutBody(planId: string, gymId: string | null | undefined, clientPlatform: 'mobile' | 'mobile_web') {
  return { membership_plan_id: planId, ...(gymId ? { gym_id: gymId } : {}), client_platform: clientPlatform };
}

// Says plainly that the home gym only changes after payment succeeds.
export function gymChangeNotice(selectedName: string | null, selectedId: string | null | undefined, homeName: string | null | undefined, homeId: string | null | undefined) {
  const target = selectedName ?? 'the selected gym';
  if (homeId && selectedId && homeId !== selectedId) {
    return `Your home gym changes to ${target} only after payment succeeds. Until then you keep using ${homeName ?? 'your current gym'}.`;
  }
  return `Your home gym only changes after a payment succeeds. This membership is for ${target}.`;
}
