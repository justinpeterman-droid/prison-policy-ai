export const WEB_API_BASE = "/api/web/v1";
export const WEB_CLIENT_VERSION = "0.1.0";

export interface ApiErrorBody {
  code: string;
  message: string;
  retryable: boolean;
  details: Record<string, unknown>;
}

export class WebApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly retryable: boolean;
  readonly requestId: string | null;

  constructor(options: {
    code: string;
    message: string;
    status: number;
    retryable?: boolean;
    requestId?: string | null;
  }) {
    super(options.message);
    this.name = "WebApiError";
    this.code = options.code;
    this.status = options.status;
    this.retryable = options.retryable ?? false;
    this.requestId = options.requestId ?? null;
  }
}

function requestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function readCookie(name: string): string | null {
  const prefix = `${encodeURIComponent(name)}=`;
  for (const part of document.cookie.split(";")) {
    const value = part.trim();
    if (value.startsWith(prefix)) {
      return decodeURIComponent(value.slice(prefix.length));
    }
  }
  return null;
}

function isMutation(method: string): boolean {
  return !["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase());
}

export async function webApiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const method = init.method ?? "GET";
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  headers.set("X-Client-Version", WEB_CLIENT_VERSION);
  headers.set("X-Request-ID", requestId());
  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (isMutation(method) && !path.endsWith("/auth/login")) {
    const csrf = readCookie("slut_web_csrf");
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }

  let response: Response;
  try {
    response = await fetch(`${WEB_API_BASE}${path}`, {
      ...init,
      method,
      headers,
      credentials: "include",
    });
  } catch {
    throw new WebApiError({
      code: "network_unavailable",
      message: "The service could not be reached. Your visible work has not been cleared.",
      status: 0,
      retryable: true,
    });
  }

  const requestReference = response.headers.get("X-Request-ID");
  const payload = await response.json().catch(() => null) as
    | { data?: T; error?: ApiErrorBody; request_id?: string }
    | null;

  if (!response.ok || payload?.error) {
    const error = payload?.error;
    throw new WebApiError({
      code: error?.code ?? "unexpected_response",
      message: error?.message ?? "The request could not be completed.",
      status: response.status,
      retryable: error?.retryable ?? false,
      requestId: payload?.request_id ?? requestReference,
    });
  }
  if (!payload || !("data" in payload)) {
    throw new WebApiError({
      code: "unexpected_response",
      message: "The service returned an unreadable response.",
      status: response.status,
      requestId: requestReference,
    });
  }
  return payload.data as T;
}
