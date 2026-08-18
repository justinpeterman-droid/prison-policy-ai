const JSON_HEADERS = {
  Accept: "application/json",
  "Content-Type": "application/json",
} as const;

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const CSRF_COOKIE_NAMES = ["__Host-web-csrf", "web-csrf"];

export const designPreviewEnabled = import.meta.env.VITE_DESIGN_PREVIEW === "true";

export interface ApiEnvelope<T> {
  data: T;
  request_id: string;
  server_time: string;
  api_version: string;
}

export interface ApiFailureEnvelope {
  error: {
    code: string;
    message: string;
    retryable: boolean;
    details?: Record<string, unknown>;
  };
  request_id?: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryable: boolean;
  readonly details?: Record<string, unknown>;
  readonly requestId?: string;

  constructor(
    message: string,
    options: {
      status: number;
      code?: string;
      retryable?: boolean;
      details?: Record<string, unknown>;
      requestId?: string;
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code ?? "request_failed";
    this.retryable = options.retryable ?? false;
    this.details = options.details;
    this.requestId = options.requestId;
  }
}

function cookieValue(name: string): string | null {
  const prefix = `${encodeURIComponent(name)}=`;
  const match = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  return match ? decodeURIComponent(match.slice(prefix.length)) : null;
}

function csrfToken(): string | null {
  for (const name of CSRF_COOKIE_NAMES) {
    const value = cookieValue(name);
    if (value) return value;
  }
  return null;
}

export function requestId(prefix = "web"): string {
  const uuid = crypto.randomUUID().replaceAll("-", "");
  return `${prefix}_${uuid}`.slice(0, 64);
}

async function parseFailure(response: Response): Promise<ApiError> {
  let body: ApiFailureEnvelope | null = null;
  try {
    body = (await response.json()) as ApiFailureEnvelope;
  } catch {
    // The server may return an HTML proxy error. Keep the user-facing message generic.
  }
  return new ApiError(
    body?.error?.message ?? "The request could not be completed.",
    {
      status: response.status,
      code: body?.error?.code,
      retryable: body?.error?.retryable,
      details: body?.error?.details,
      requestId: body?.request_id ?? response.headers.get("X-Request-ID") ?? undefined,
    },
  );
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", JSON_HEADERS.Accept);
  headers.set("X-Request-ID", headers.get("X-Request-ID") ?? requestId());

  if (init.body !== undefined && !(init.body instanceof FormData)) {
    headers.set("Content-Type", JSON_HEADERS["Content-Type"]);
  }
  if (UNSAFE_METHODS.has(method)) {
    const token = csrfToken();
    if (token) headers.set("X-CSRF-Token", token);
  }

  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      method,
      headers,
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch {
    throw new ApiError("The service could not be reached. Check your connection and try again.", {
      status: 0,
      code: "network_unavailable",
      retryable: true,
    });
  }

  if (!response.ok) throw await parseFailure(response);
  if (response.status === 204) return undefined as T;

  const body = (await response.json()) as ApiEnvelope<T>;
  return body.data;
}

export async function downloadAuthorizedFile(
  path: string,
  filename: string,
  init: RequestInit = {},
): Promise<void> {
  const method = (init.method ?? "POST").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("X-Request-ID", headers.get("X-Request-ID") ?? requestId("export"));
  if (UNSAFE_METHODS.has(method)) {
    const token = csrfToken();
    if (token) headers.set("X-CSRF-Token", token);
  }

  const response = await fetch(path, {
    ...init,
    method,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) throw await parseFailure(response);

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
