import { webApiRequest } from "../../api/client";

export interface SessionProfileApi {
  account_id: string;
  staff_id: string;
  session_id: string;
  employee_number: string;
  display_name: string;
  rank: string | null;
  shift: string | null;
  role: "user" | "admin";
  must_change_pin: boolean;
}

export interface SessionProfile {
  accountId: string;
  staffId: string;
  sessionId: string;
  employeeNumber: string;
  displayName: string;
  rank: string | null;
  shift: string | null;
  role: "user" | "admin";
  mustChangePin: boolean;
}

interface SessionResponseApi {
  authenticated: boolean;
  profile: SessionProfileApi | null;
}

export interface SessionState {
  authenticated: boolean;
  profile: SessionProfile | null;
}

function requireString(value: unknown, field: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Invalid session profile field: ${field}`);
  }
  return value;
}

export function toSessionProfile(value: SessionProfileApi): SessionProfile {
  if (value.role !== "user" && value.role !== "admin") {
    throw new Error("Invalid session profile role");
  }
  return {
    accountId: requireString(value.account_id, "account_id"),
    staffId: requireString(value.staff_id, "staff_id"),
    sessionId: requireString(value.session_id, "session_id"),
    employeeNumber: requireString(value.employee_number, "employee_number"),
    displayName: requireString(value.display_name, "display_name"),
    rank: value.rank,
    shift: value.shift,
    role: value.role,
    mustChangePin: Boolean(value.must_change_pin),
  };
}

function toSessionState(value: SessionResponseApi): SessionState {
  return {
    authenticated: value.authenticated,
    profile: value.profile ? toSessionProfile(value.profile) : null,
  };
}

export async function getBrowserSession(): Promise<SessionState> {
  return toSessionState(
    await webApiRequest<SessionResponseApi>("/auth/session"),
  );
}

export async function loginBrowserSession(input: {
  employeeNumber: string;
  pin: string;
  persistent: boolean;
}): Promise<SessionState> {
  return toSessionState(
    await webApiRequest<SessionResponseApi>("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        employee_number: input.employeeNumber,
        pin: input.pin,
        persistent: input.persistent,
      }),
    }),
  );
}

export async function renewBrowserSession(): Promise<SessionState> {
  return toSessionState(
    await webApiRequest<SessionResponseApi>("/auth/renew", { method: "POST" }),
  );
}

export async function logoutBrowserSession(): Promise<void> {
  await webApiRequest<{ signed_out: boolean }>("/auth/logout", { method: "POST" });
}
