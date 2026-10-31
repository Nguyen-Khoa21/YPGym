import type { Action, Credentials, ScannerMode } from './types.ts';

export function parseCredentials(value: string | null): Credentials | null {
  if (!value) return null;
  try {
    const parsed = JSON.parse(value) as Partial<Credentials>;
    if (!parsed.apiBaseUrl || !parsed.deviceId || !parsed.apiKey || !['both', 'check_in', 'check_out'].includes(parsed.mode ?? '')) return null;
    return parsed as Credentials;
  } catch { return null; }
}

export function serializeCredentials(credentials: Credentials): string {
  return JSON.stringify(credentials);
}

export function initialActionForMode(mode: ScannerMode): Action {
  return mode === 'check_out' ? 'check_out' : 'check_in';
}
