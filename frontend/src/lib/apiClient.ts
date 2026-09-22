import type { ApiErrorPayload } from "@/lib/apiErrors";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001/api/v1";

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

  const response = await fetch(apiUrl(path), {
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
      throw data;
    }
    throw {
      error: {
        code: "HTTP_ERROR",
        message: typeof data === "string" ? data : "The request failed.",
        details: null,
      },
    } satisfies ApiErrorPayload;
  }

  return data as T;
}

export async function downloadApiFile(path: string, token?: string | null): Promise<Blob> {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(apiUrl(path), { headers });
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event("ypgym:unauthorized"));
    const data = await response.json().catch(() => null);
    if (isApiErrorPayload(data)) throw data;
    throw { error: { code: "HTTP_ERROR", message: "The file could not be downloaded.", details: null } } satisfies ApiErrorPayload;
  }
  return response.blob();
}

export async function uploadApiImage<T>(path: string, file: File, token?: string | null): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(apiUrl(path), {
    method: "PUT",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body,
  });
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event("ypgym:unauthorized"));
    if (isApiErrorPayload(data)) throw data;
    throw { error: { code: "HTTP_ERROR", message: "The image could not be uploaded.", details: null } } satisfies ApiErrorPayload;
  }
  return data as T;
}

function isApiErrorPayload(value: unknown): value is ApiErrorPayload {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<ApiErrorPayload>;
  return !!candidate.error && typeof candidate.error.message === "string";
}
