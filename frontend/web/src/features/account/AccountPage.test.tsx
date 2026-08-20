import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SessionProfile } from "../auth/api";
import { AccountPage } from "./AccountPage";
import {
  fetchAccountSessions,
  logoutAllAccountSessions,
  revokeAccountSession,
  signOutCurrentBrowserSession,
} from "./api";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    fetchAccountSessions: vi.fn(),
    revokeAccountSession: vi.fn(),
    logoutAllAccountSessions: vi.fn(),
    signOutCurrentBrowserSession: vi.fn(),
    changePin: vi.fn(),
  };
});

const profile: SessionProfile = {
  accountId: "00000000-0000-4000-8000-000000000001",
  staffId: "00000000-0000-4000-8000-000000000002",
  sessionId: "00000000-0000-4000-8000-000000000003",
  employeeNumber: "F-1001",
  displayName: "Officer Casey Morgan",
  rank: "Officer",
  shift: "A",
  role: "user",
  mustChangePin: false,
};

const reload = vi.fn();

beforeEach(() => {
  vi.mocked(fetchAccountSessions).mockResolvedValue([
    {
      sessionId: profile.sessionId,
      deviceLabel: "Current browser",
      createdAt: "2026-08-19T12:00:00Z",
      lastSeenAt: "2026-08-19T13:00:00Z",
      expiresAt: "2026-09-18T12:00:00Z",
      current: true,
    },
    {
      sessionId: "00000000-0000-4000-8000-000000000010",
      deviceLabel: "Other browser",
      createdAt: "2026-08-18T12:00:00Z",
      lastSeenAt: "2026-08-18T13:00:00Z",
      expiresAt: "2026-09-17T12:00:00Z",
      current: false,
    },
  ]);
  vi.mocked(revokeAccountSession).mockResolvedValue(undefined);
  vi.mocked(logoutAllAccountSessions).mockResolvedValue(undefined);
  vi.mocked(signOutCurrentBrowserSession).mockResolvedValue(undefined);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Account page", () => {
  it("shows read-only employee identity and active browser sessions", async () => {
    render(<AccountPage profile={profile} onAuthenticationChanged={reload} />);

    expect(screen.getByRole("heading", { name: "My Account" })).toBeInTheDocument();
    const identity = screen.getByRole("region", { name: "Employee identity" });
    expect(within(identity).getByText("Officer Casey Morgan")).toBeInTheDocument();
    expect(within(identity).getByText("F-1001")).toBeInTheDocument();
    expect(within(identity).queryByRole("textbox")).not.toBeInTheDocument();
    expect(await screen.findByText("Current browser")).toBeInTheDocument();
    expect(screen.getByText("Other browser")).toBeInTheDocument();
  });

  it("revokes another session but not through the current-session row", async () => {
    render(<AccountPage profile={profile} onAuthenticationChanged={reload} />);
    const other = await screen.findByRole("article", { name: "Other browser" });
    fireEvent.click(within(other).getByRole("button", { name: "Sign out Other browser" }));

    await waitFor(() => expect(revokeAccountSession).toHaveBeenCalledWith(
      "00000000-0000-4000-8000-000000000010",
    ));
    expect(screen.queryByText("Other browser")).not.toBeInTheDocument();

    const current = screen.getByRole("article", { name: "Current browser" });
    expect(within(current).queryByRole("button", { name: /Sign out Current browser/ })).not.toBeInTheDocument();
  });

  it("signs out the current browser and all sessions through explicit actions", async () => {
    render(<AccountPage profile={profile} onAuthenticationChanged={reload} />);
    await screen.findByText("Current browser");

    fireEvent.click(screen.getByRole("button", { name: "Sign out this device" }));
    await waitFor(() => expect(signOutCurrentBrowserSession).toHaveBeenCalled());
    expect(reload).toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Sign out everywhere" }));
    await waitFor(() => expect(logoutAllAccountSessions).toHaveBeenCalled());
  });

  it("shows a recoverable session-list error", async () => {
    vi.mocked(fetchAccountSessions).mockRejectedValueOnce(new Error("Session service unavailable."));
    render(<AccountPage profile={profile} onAuthenticationChanged={reload} />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Session service unavailable");
    expect(alert.className).toBe("account-state error");
    expect(alert).toHaveAttribute("aria-live", "assertive");
    expect(alert).toHaveAttribute("aria-atomic", "true");
    expect(screen.getByRole("button", { name: "Try sessions again" })).toBeInTheDocument();
  });
});
