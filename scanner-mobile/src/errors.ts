import type { ScannerError } from './types.ts';

const guidance: Record<string, string> = {
  INVALID_DEVICE: 'Device unavailable. Stop scanning and reprovision or contact an administrator.',
  INVALID_TOKEN: 'QR is invalid. Ask the member to reopen My QR.',
  EXPIRED_TOKEN: 'QR expired. Ask the member to wait for it to refresh.',
  SUPERSEDED_TOKEN: 'A newer QR exists. Scan the latest code.',
  INACTIVE_MEMBERSHIP: 'Entry denied. Review the membership guidance with the member.',
  DUPLICATE_SCAN: 'Already scanned recently. Do not immediately retry.',
  ACTIVE_SESSION_EXISTS: 'This member is already checked in.',
  NO_ACTIVE_SESSION: 'No active session exists to check out.',
  QR_STATE_UNAVAILABLE: 'QR verification is temporarily unavailable.',
  SCAN_STATE_UNAVAILABLE: 'Duplicate protection is temporarily unavailable.',
  VALIDATION_ERROR: 'The QR could not be submitted. Ask the member to reopen My QR.',
};

export function staffGuidance(error: ScannerError) {
  if (error.code === 'INACTIVE_MEMBERSHIP' && error.message) return error.message;
  return guidance[error.code] ?? 'The scan could not be completed. Try a fresh QR or contact an administrator.';
}

export function isDeviceBlocked(code: string) { return code === 'INVALID_DEVICE'; }
export function isNetworkError(code: string) { return code === 'NETWORK_ERROR'; }
