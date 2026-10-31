import type { Action, Credentials, ScanResult, ScannerError } from './types.ts';

export class ScannerApiError extends Error implements ScannerError {
  readonly code: string;
  readonly requestId?: string;

  constructor(code: string, message: string, requestId?: string) {
    super(message);
    this.name = 'ScannerApiError';
    this.code = code;
    this.requestId = requestId;
  }
}

export async function verifyDevice(credentials: Credentials, fetcher: typeof fetch = fetch) {
  return request<{ device_id: string; display_name: string; status: 'active' }>(credentials, '/attendance/device/verify', { device_id: credentials.deviceId }, fetcher);
}

export async function submitScan(credentials: Credentials, action: Action, qrToken: string, fetcher: typeof fetch = fetch) {
  if (qrToken.length < 20 || qrToken.length > 4096) throw new ScannerApiError('INVALID_TOKEN', 'The QR payload length is invalid.');
  return request<ScanResult>(credentials, action === 'check_in' ? '/attendance/check-in' : '/attendance/check-out', { device_id: credentials.deviceId, qr_token: qrToken }, fetcher);
}

async function request<T>(credentials: Credentials, path: string, body: unknown, fetcher: typeof fetch): Promise<T> {
  let response: Response;
  try {
    response = await fetcher(`${credentials.apiBaseUrl.replace(/\/$/, '')}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Device-Api-Key': credentials.apiKey },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ScannerApiError('NETWORK_ERROR', 'No attendance was confirmed. Check the connection and scan a fresh QR.');
  }
  const requestId = response.headers.get('x-request-id') || undefined;
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error = (payload as { error?: { code?: string; message?: string } } | null)?.error;
    throw new ScannerApiError(error?.code ?? 'HTTP_ERROR', error?.message ?? 'The scanner request failed.', requestId);
  }
  return payload as T;
}
