export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly code: string) { super(message); }
}

const baseUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '');

export async function apiRequest<T>(path: string, token?: string | null, options: { method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'; body?: unknown; signal?: AbortSignal } = {}): Promise<T> {
  if (!baseUrl) throw new ApiError('Set EXPO_PUBLIC_API_URL to your reachable backend address. See mobile/README.md.', 0, 'CONFIGURATION_ERROR');
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method: options.method ?? 'GET',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError('The API cannot be reached. Check the server and your device network.', 0, 'NETWORK_ERROR');
  }
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const payload = data as { error?: { code?: string; message?: string } } | null;
    throw new ApiError(payload?.error?.message ?? `Request failed (${response.status}).`, response.status, payload?.error?.code ?? 'HTTP_ERROR');
  }
  return data as T;
}

export function errorMessage(error: unknown) { return error instanceof Error ? error.message : 'Something went wrong. Please try again.'; }
export const formatMoney = (amount: string | number) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(Number(amount));
export const GYM_TIMEZONE = process.env.EXPO_PUBLIC_GYM_TIMEZONE || 'Asia/Ho_Chi_Minh';
export const formatDate = (value: string) => /^\d{4}-\d{2}-\d{2}$/.test(value)
  ? new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
  : new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short', year: 'numeric', timeZone: GYM_TIMEZONE }).format(new Date(value));
export const formatTime = (value: string) => new Intl.DateTimeFormat('en', { hour: '2-digit', minute: '2-digit', timeZone: GYM_TIMEZONE }).format(new Date(value));
