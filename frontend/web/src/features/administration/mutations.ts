import { webApiRequest } from "../../api/client";
import { mutationHeaders, runWithStepUp, type AdminPurpose } from "./api";

export interface TemporaryPinResult {
  account_id: string;
  temporary_pin: string;
  temporary_pin_expires_at: string | null;
}

async function withStepUp<T>(pin: string, purpose: AdminPurpose, action: () => Promise<T>): Promise<T> {
  return runWithStepUp(pin, purpose, action);
}

export async function createStaff(input: {
  employeeNumber: string;
  rank: string | null;
  firstName: string;
  lastName: string;
  shift: string | null;
}, pin: string) {
  return withStepUp(pin, "staff_write", () => webApiRequest<unknown>("/admin/staff", {
    method: "POST",
    headers: mutationHeaders(),
    body: JSON.stringify({
      employee_number: input.employeeNumber,
      rank: input.rank,
      first_name: input.firstName,
      last_name: input.lastName,
      shift: input.shift,
    }),
  }));
}

export async function createAccount(staffId: string, role: "user" | "admin", pin: string): Promise<TemporaryPinResult> {
  return withStepUp(pin, "account_create", () => webApiRequest<TemporaryPinResult>("/admin/accounts", {
    method: "POST",
    headers: mutationHeaders(),
    body: JSON.stringify({ staff_id: staffId, role }),
  }));
}

export async function resetAccountPin(accountId: string, pin: string): Promise<TemporaryPinResult> {
  return withStepUp(pin, "account_reset_pin", () => webApiRequest<TemporaryPinResult>(`/admin/accounts/${accountId}/reset-pin`, {
    method: "POST",
    headers: mutationHeaders(),
  }));
}

export async function unlockAccount(accountId: string, pin: string) {
  return withStepUp(pin, "account_unlock", () => webApiRequest<unknown>(`/admin/accounts/${accountId}/unlock`, {
    method: "POST",
    headers: mutationHeaders(),
  }));
}

export async function updateAccount(
  accountId: string,
  role: "user" | "admin",
  status: string,
  pin: string,
) {
  return withStepUp(pin, "account_role_status", () => webApiRequest<unknown>(`/admin/accounts/${accountId}`, {
    method: "PATCH",
    headers: mutationHeaders(),
    body: JSON.stringify({ role, status }),
  }));
}

export async function revokeAccountSessions(accountId: string, pin: string) {
  return withStepUp(pin, "account_revoke_sessions", () => webApiRequest<unknown>(`/admin/accounts/${accountId}/revoke-sessions`, {
    method: "POST",
    headers: mutationHeaders(),
    body: JSON.stringify({ scope: "all" }),
  }));
}
