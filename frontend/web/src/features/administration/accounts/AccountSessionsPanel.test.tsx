import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AccountSessionsPanel } from "./AccountSessionsPanel";
import * as accountApi from "./api";

vi.mock("./api", () => ({
  listAccountSessions: vi.fn(),
  revokeAccountSession: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("administrator account sessions", () => {
  it("shows safe device/session metadata and requires confirmation before revocation", async () => {
    vi.mocked(accountApi.listAccountSessions).mockResolvedValue([
      {
        sessionId: "session-1",
        deviceLabel: "Training laptop",
        persistent: true,
        lastUsedAt: "2026-08-20T01:00:00Z",
        accessExpiresAt: "2026-08-20T02:00:00Z",
        revokedAt: null,
      },
    ]);

    render(<AccountSessionsPanel accountId="account-1" />);

    expect(await screen.findByText("Training laptop")).toBeInTheDocument();
    expect(screen.getByText(/Persistent session/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Revoke Training laptop" }));
    expect(screen.getByRole("heading", { name: "Confirm session revocation" })).toBeInTheDocument();
    expect(accountApi.revokeAccountSession).not.toHaveBeenCalled();
  });
});
