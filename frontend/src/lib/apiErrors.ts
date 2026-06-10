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

export type UiError = {
  code: ApiErrorCode | string;
  title: string;
  message: string;
  details?: unknown;
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
      code: "NETWORK_ERROR",
      title: "Request failed",
      message: error.message || fallbackMessages.NETWORK_ERROR,
    };
  }

  return {
    code: "UNKNOWN_ERROR",
    title: "Unexpected error",
    message: fallbackMessages.UNKNOWN_ERROR,
  };
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
