import { webApiRequest } from "../../api/client";
import { ACCOUNT_PIN_FIELDS, ACCOUNT_ROUTES } from "./route-manifest";

export interface AccountSession {
  sessionId: string;
  deviceLabel: string;
  createdAt: string | null;
  lastSeenAt: string | null;
  expiresAt: string | null;
  current: boolean;
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const CREDENTIAL_KEYS = new Set([
  "access_token",
  "renewal_token",
  "csrf_token",
  "pin",
  "pin_hash",
  "current_pin",
  "new_pin",
]);

function object(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`${label} is invalid.`);
  }
  return value as Record<string, unknown>;
}

function optionalTimestamp(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string" || !Number.isFinite(Date.parse(value))) {
    throw new Error("Session time is invalid.");
  }
  return value;
}

function sessionId(row: Record<string, unknown>): string {
  const value = row.session_id ?? row.id;
  if (typeof value !== "string" || !UUID.test(value)) {
    throw new Error("Session ID is invalid.");
  }
  return value;
}

function rejectCredentials(value: unknown): void {
  if (typeof value !== "object" || value === null) return;
  if (Array.isArray(value)) {
    value.forEach(rejectCredentials);
    return;
  }
  for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
    if (CREDENTIAL_KEYS.has(key.toLowerCase()) || key.toLowerCase().endsWith("_token")) {
      throw new Error("The account response exposed a readable credential.");
    }
    rejectCredentials(item);
  }
}

export function parseAccountSessions(value: unknown): AccountSession[] {
  rejectCredentials(value);
  const envelope = object(value, "Account sessions");
  const rawItems = Array.isArray(envelope.items)
    ? envelope.items
    : Array.isArray(envelope.sessions)
      ? envelope.sessions
      : null;
  if (!rawItems) throw new Error("Account sessions are invalid.");
  return rawItems.map((rawItem, index) => {
    const row = object(rawItem, `Account session ${index + 1}`);
    const device = row.device_name ?? row.device_label ?? row.device_id ?? "Browser session";
    if (typeof device !== "string" || device.length > 200) {
      throw new Error("Session device is invalid.");
    }
    const current = row.current ?? row.is_current ?? false;
    if (typeof current !== "boolean") throw new Error("Current-session marker is invalid.");
    return {
      sessionId: sessionId(row),
      deviceLabel: device.trim() || "Browser session",
      createdAt: optionalTimestamp(row.created_at),
      lastSeenAt: optionalTimestamp(row.last_seen_at ?? row.updated_at),
      expiresAt: optionalTimestamp(row.expires_at),
      current,
    };
  });
}

function accountPath(path: string): string {
  return `/account${path}`;
}

function validatePin(value: string): string {
  if (!/^[A-Za-z0-9]{4,8}$/.test(value)) {
    throw new Error("PINs must contain 4 through 8 letters or numbers.");
  }
  return value;
}

export async function changePin(currentPin: string, newPin: string): Promise<void> {
  const current = validatePin(currentPin);
  const replacement = validatePin(newPin);
  if (current === replacement) throw new Error("Choose a different new PIN.");
  const body: Record<string, string> = {
    [ACCOUNT_PIN_FIELDS.current]: current,
    [ACCOUNT_PIN_FIELDS.newPin]: replacement,
  };
  if (ACCOUNT_PIN_FIELDS.confirm) body[ACCOUNT_PIN_FIELDS.confirm] = replacement;
  await webApiRequest<unknown>(accountPath(ACCOUNT_ROUTES.changePin.path), {
    method: ACCOUNT_ROUTES.changePin.method,
    body: JSON.stringify(body),
  });
}

export async function fetchAccountSessions(): Promise<AccountSession[]> {
  const raw = await webApiRequest<unknown>(accountPath(ACCOUNT_ROUTES.sessions.path), {
    method: ACCOUNT_ROUTES.sessions.method,
  });
  return parseAccountSessions(raw);
}

function replaceSessionPath(path: string, id: string): string {
  if (!UUID.test(id)) throw new Error("Session ID is invalid.");
  if (!/<[^>]+>/.test(path)) throw new Error("Session route is invalid.");
  return path.replace(/<[^>]+>/, encodeURIComponent(id));
}

export async function revokeAccountSession(id: string): Promise<void> {
  await webApiRequest<unknown>(
    accountPath(replaceSessionPath(ACCOUNT_ROUTES.revokeSession.path, id)),
    { method: ACCOUNT_ROUTES.revokeSession.method },
  );
}

export async function logoutAllAccountSessions(): Promise<void> {
  await webApiRequest<unknown>(accountPath(ACCOUNT_ROUTES.logoutAll.path), {
    method: ACCOUNT_ROUTES.logoutAll.method,
  });
}
