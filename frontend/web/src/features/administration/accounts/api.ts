import { z } from "zod";
import { webApiRequest } from "../../../api/client";
import { mutationHeaders, runWithStepUp } from "../api";

const sessionPageSchema = z.object({
  items: z.array(z.object({
    session_id: z.string(),
    device_label: z.string(),
    persistent: z.boolean(),
    last_used_at: z.string().nullable(),
    created_at: z.string().nullable(),
    access_expires_at: z.string().nullable(),
    renewal_expires_at: z.string().nullable(),
    revoked_at: z.string().nullable(),
    revoke_reason: z.string().nullable(),
  }).strict()),
  next_cursor: z.string().nullable(),
}).strict();

export interface AdminAccountSession {
  sessionId: string;
  deviceLabel: string;
  persistent: boolean;
  lastUsedAt: string | null;
  accessExpiresAt: string | null;
  revokedAt: string | null;
}

export async function listAccountSessions(accountId: string): Promise<AdminAccountSession[]> {
  const value = sessionPageSchema.parse(
    await webApiRequest<unknown>(`/admin/accounts/${accountId}/sessions?limit=50`),
  );
  return value.items.map((item) => ({
    sessionId: item.session_id,
    deviceLabel: item.device_label,
    persistent: item.persistent,
    lastUsedAt: item.last_used_at,
    accessExpiresAt: item.access_expires_at,
    revokedAt: item.revoked_at,
  }));
}

export async function revokeAccountSession(
  accountId: string,
  sessionId: string,
  pin: string,
): Promise<void> {
  await runWithStepUp(pin, "account_revoke_sessions", () => webApiRequest<unknown>(
    `/admin/accounts/${accountId}/revoke-sessions`,
    {
      method: "POST",
      headers: mutationHeaders(),
      body: JSON.stringify({ scope: "one", session_id: sessionId }),
    },
  ));
}

export async function updateStaffProfile(
  staffId: string,
  input: {
    employeeNumber?: string;
    rank?: string | null;
    firstName?: string;
    lastName?: string;
    shift?: string | null;
    isActive?: boolean;
  },
  pin: string,
): Promise<void> {
  const payload: Record<string, unknown> = {};
  if (input.employeeNumber !== undefined) payload.employee_number = input.employeeNumber;
  if (input.rank !== undefined) payload.rank = input.rank;
  if (input.firstName !== undefined) payload.first_name = input.firstName;
  if (input.lastName !== undefined) payload.last_name = input.lastName;
  if (input.shift !== undefined) payload.shift = input.shift;
  if (input.isActive !== undefined) payload.is_active = input.isActive;
  await runWithStepUp(pin, "staff_write", () => webApiRequest<unknown>(`/admin/staff/${staffId}`, {
    method: "PATCH",
    headers: mutationHeaders(),
    body: JSON.stringify(payload),
  }));
}
