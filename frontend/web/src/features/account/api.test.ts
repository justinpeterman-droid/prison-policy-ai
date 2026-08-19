import { describe, expect, it, vi } from "vitest";
import { changePin, parseAccountSessions, revokeAccountSession } from "./api";

const request = vi.fn(async (_path: string, _init?: RequestInit) => ({}));
vi.mock("../../api/client", () => ({
  webApiRequest: (path: string, init?: RequestInit) => request(path, init),
}));

vi.mock("./route-manifest", () => ({
  ACCOUNT_ROUTES: {
    changePin: { method: "POST", path: "/change-pin", bodyFields: ["current_pin", "new_pin"] },
    logoutAll: { method: "POST", path: "/logout-all", bodyFields: [] },
    sessions: { method: "GET", path: "/sessions", bodyFields: [] },
    revokeSession: { method: "DELETE", path: "/sessions/<uuid:session_id>", bodyFields: [] },
  },
  ACCOUNT_PIN_FIELDS: { current: "current_pin", newPin: "new_pin", confirm: null },
}));

describe("personal account API", () => {
  it("builds the server-owned PIN request fields without returning PIN values", async () => {
    await changePin("1234", "5678");

    expect(request).toHaveBeenCalledWith("/account/change-pin", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ current_pin: "1234", new_pin: "5678" }),
    }));
    expect(await changePin("1234", "5678")).toBeUndefined();
  });

  it("replaces only the declared UUID path parameter", async () => {
    await revokeAccountSession("00000000-0000-4000-8000-000000000010");

    expect(request).toHaveBeenCalledWith(
      "/account/sessions/00000000-0000-4000-8000-000000000010",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("parses safe session metadata and rejects readable credentials", () => {
    const sessions = parseAccountSessions({
      items: [{
        session_id: "00000000-0000-4000-8000-000000000010",
        device_id: "Browser session",
        created_at: "2026-08-19T12:00:00Z",
        last_seen_at: "2026-08-19T13:00:00Z",
        expires_at: "2026-09-18T12:00:00Z",
        current: true,
      }],
    });
    expect(sessions[0]?.current).toBe(true);
    expect(JSON.stringify(sessions)).not.toContain("token");

    expect(() => parseAccountSessions({
      items: [{
        session_id: "00000000-0000-4000-8000-000000000010",
        access_token: "forbidden",
      }],
    })).toThrow(/credential/i);
  });
});
