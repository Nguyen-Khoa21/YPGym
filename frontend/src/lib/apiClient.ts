import { ApiError, type ApiErrorPayload } from "./apiErrors.ts";

export const API_BASE_URL =
  import.meta.env?.VITE_API_BASE_URL ?? "http://localhost:8001/api/v1";

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  token?: string | null;
  headers?: HeadersInit;
  signal?: AbortSignal;
};

export function apiUrl(path: string) {
  if (path.startsWith("http")) {
    return path;
  }
  return `${API_BASE_URL}${path}`;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const response = await safeFetch(apiUrl(path), {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  const contentType = response.headers.get("content-type") ?? "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    if (response.status === 401) {
      window.dispatchEvent(new Event("ypgym:unauthorized"));
    }
    if (isApiErrorPayload(data)) {
      throw fromPayload(data, response);
    }
    throw new ApiError("HTTP_ERROR", "The request failed.", response.status, null, requestId(response));
  }

  return data as T;
}

export async function downloadApiFile(path: string, token?: string | null): Promise<Blob> {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await safeFetch(apiUrl(path), { headers });
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event("ypgym:unauthorized"));
    const data = await response.json().catch(() => null);
    if (isApiErrorPayload(data)) throw fromPayload(data, response);
    throw new ApiError("HTTP_ERROR", "The file could not be downloaded.", response.status, null, requestId(response));
  }
  return response.blob();
}

export async function uploadApiImage<T>(path: string, file: File, token?: string | null): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  const response = await safeFetch(apiUrl(path), {
    method: "PUT",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body,
  });
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event("ypgym:unauthorized"));
    if (isApiErrorPayload(data)) throw fromPayload(data, response);
    throw new ApiError("HTTP_ERROR", "The image could not be uploaded.", response.status, null, requestId(response));
  }
  return data as T;
}

async function safeFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (error) {
    if (init?.signal?.aborted) throw error;
    throw new ApiError("NETWORK_ERROR", "The server could not be reached.", 0);
  }
}

function requestId(response: Response): string | undefined {
  return response.headers.get("x-request-id") || undefined;
}

function fromPayload(payload: ApiErrorPayload, response: Response): ApiError {
  return new ApiError(
    payload.error.code,
    payload.error.message || "The request failed.",
    response.status,
    payload.error.details,
    requestId(response),
  );
}

function isApiErrorPayload(value: unknown): value is ApiErrorPayload {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<ApiErrorPayload>;
  return !!candidate.error && typeof candidate.error.message === "string";
}
