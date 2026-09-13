export function qrSecondsLeft(expiresAt: string | undefined, now: number) {
  if (!expiresAt) return 0;
  const expiry = Date.parse(expiresAt);
  return Number.isFinite(expiry) ? Math.max(0, Math.ceil((expiry - now) / 1000)) : 0;
}

export function mayShowQr(eligible: boolean, foregroundReady: boolean, hasError: boolean, secondsLeft: number, hasToken: boolean) {
  return eligible && foregroundReady && !hasError && secondsLeft > 0 && hasToken;
}
