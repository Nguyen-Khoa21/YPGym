// Only an expired membership (not cancelled, revoked or frozen) shows the renew or change-location panel.
export function isExpiredStatus(status: string | null | undefined) {
  return status === 'expired';
}

// "Change location" opens the renew screen with no gym preselected. The home gym itself only changes after
// a verified payment, exactly as before.
export function renewScreenParams(mode: 'renew' | 'change') {
  return mode === 'change' ? { mode: 'change' } : {};
}

export function isChangeLocation(mode: string | string[] | undefined) {
  return (Array.isArray(mode) ? mode[0] : mode) === 'change';
}
