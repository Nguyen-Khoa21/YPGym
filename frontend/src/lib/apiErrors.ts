import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

export type ApiErrorCode =
  | "VALIDATION_ERROR"
  | "AUTHENTICATION_REQUIRED"
  | "PERMISSION_DENIED"
  | "RESOURCE_NOT_FOUND"
  | "BUSINESS_RULE_CONFLICT"
  | "MEMBERSHIP_INACTIVE"
  | "HTTP_ERROR"
  | "NETWORK_ERROR"
  | "UNKNOWN_ERROR";

export type ApiErrorPayload = {
  error: {
    code: ApiErrorCode | string;
    message: string;
    details: unknown;
  };
};

export class ApiError extends Error {
  readonly code: ApiErrorCode | string;
  readonly status: number;
  readonly details: unknown;
  readonly requestId?: string;

  constructor(
    code: ApiErrorCode | string,
    message: string,
    status: number,
    details: unknown = null,
    requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
    this.requestId = requestId;
  }
}

export type UiError = {
  code: ApiErrorCode | string;
  title: string;
  message: string;
  details?: unknown;
  status?: number;
  requestId?: string;
};

const fallbackMessages: Record<ApiErrorCode, string> = {
  VALIDATION_ERROR: "Check the form fields and try again.",
  AUTHENTICATION_REQUIRED: "Sign in to continue.",
  PERMISSION_DENIED: "You do not have access to this action.",
  RESOURCE_NOT_FOUND: "The requested item could not be found.",
  BUSINESS_RULE_CONFLICT: "This action is not allowed right now.",
  MEMBERSHIP_INACTIVE: "Your membership is not active.",
  HTTP_ERROR: "The request could not be completed.",
  NETWORK_ERROR: "The server could not be reached.",
  UNKNOWN_ERROR: "Something went wrong.",
};

export function toUiError(error: unknown): UiError {
  if (error instanceof ApiError) {
    return {
      code: error.code,
      title: codeToTitle(error.code),
      message:
        error.message ||
        fallbackMessages[error.code as ApiErrorCode] ||
        fallbackMessages.UNKNOWN_ERROR,
      details: error.details,
      status: error.status,
      requestId: error.requestId,
    };
  }

  if (isApiErrorPayload(error)) {
    const code = error.error.code;
    return {
      code,
      title: codeToTitle(code),
      message:
        error.error.message ||
        fallbackMessages[code as ApiErrorCode] ||
        fallbackMessages.UNKNOWN_ERROR,
      details: error.error.details,
    };
  }

  if (error instanceof Error) {
    return {
      code: "UNKNOWN_ERROR",
      title: "Unexpected error",
      message: fallbackMessages.UNKNOWN_ERROR,
    };
  }

  return {
    code: "UNKNOWN_ERROR",
    title: "Unexpected error",
    message: fallbackMessages.UNKNOWN_ERROR,
  };
}

type ValidationIssue = {
  loc?: unknown;
  msg?: unknown;
};

export function applyApiFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  allowedFields: readonly Path<T>[],
): boolean {
  const uiError = toUiError(error);
  if (uiError.code !== "VALIDATION_ERROR" || !Array.isArray(uiError.details)) {
    return false;
  }

  const allowed = new Set<string>(allowedFields);
  let mapped = false;
  for (const issue of uiError.details as ValidationIssue[]) {
    if (!Array.isArray(issue.loc) || typeof issue.msg !== "string") continue;
    const path = issue.loc
      .filter((part) => part !== "body")
      .map(String)
      .join(".");
    if (!allowed.has(path)) continue;
    setError(path as Path<T>, { type: "server", message: issue.msg });
    mapped = true;
  }
  return mapped;
}

function isApiErrorPayload(value: unknown): value is ApiErrorPayload {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<ApiErrorPayload>;
  return (
    !!candidate.error &&
    typeof candidate.error === "object" &&
    "code" in candidate.error &&
    "message" in candidate.error
  );
}

function codeToTitle(code: string): string {
  return code
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
