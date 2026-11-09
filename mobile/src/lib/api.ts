export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;
  readonly requestId?: string;

  constructor(
    message: string,
    status: number,
    code: string,
    details: unknown = null,
    requestId?: string,
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

const baseUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '');
export function apiUrl(path: string) { return baseUrl ? `${baseUrl}${path}` : ''; }

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
    const payload = data as { error?: { code?: string; message?: string; details?: unknown } } | null;
    throw new ApiError(
      payload?.error?.message ?? 'The request could not be completed.',
      response.status,
      payload?.error?.code ?? 'HTTP_ERROR',
      payload?.error?.details ?? null,
      response.headers.get('x-request-id') || undefined,
    );
  }
  return data as T;
}

// Fixed member-facing wording for gym refusals. Other backend messages pass through unchanged.
export const gymErrorMessages: Record<string, string> = {
  GYM_SELECTION_REQUIRED: 'Choose the gym you want to join before paying.',
  MEMBERSHIP_GYM_MISMATCH: 'This membership belongs to a different gym. Please use the entrance at your home gym.',
  ATTENDANCE_GYM_MISMATCH: 'You checked in at a different YPGym location. Please check out there.',
  CLASS_GYM_INACTIVE: 'This class\'s gym is not taking bookings right now.',
};
export function errorMessage(error: unknown) {
  if (!(error instanceof ApiError)) return 'Something went wrong. Please try again.';
  const known = gymErrorMessages[error.code];
  if (known) return known;
  if (error.code === 'RESOURCE_NOT_FOUND' && /gym location/i.test(error.message)) return 'That gym is no longer available. Please pick another gym.';
  return error.message;
}
export const formatMoney = (amount: string | number) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(Number(amount));
export const GYM_TIMEZONE = process.env.EXPO_PUBLIC_GYM_TIMEZONE || 'Asia/Ho_Chi_Minh';
export const formatDate = (value: string) => /^\d{4}-\d{2}-\d{2}$/.test(value)
  ? new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
  : new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short', year: 'numeric', timeZone: GYM_TIMEZONE }).format(new Date(value));
export const formatTime = (value: string) => new Intl.DateTimeFormat('en', { hour: '2-digit', minute: '2-digit', timeZone: GYM_TIMEZONE }).format(new Date(value));
