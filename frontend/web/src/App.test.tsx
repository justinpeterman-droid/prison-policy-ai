import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { signOutCurrentBrowserSession } from "./features/account/api";
import type { SessionProfile } from "./features/auth/api";
import { fetchOfficerHomeSummary } from "./features/dashboard/api";

vi.mock("./features/dashboard/api", () => ({
  fetchOfficerHomeSummary: vi.fn(async () => ({
    continueIncident: null,
    recentIncidents: [],
    quickForms: [],
    countSheet: null,
  })),
}));

vi.mock("./features/account/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./features/account/api")>()),
  signOutCurrentBrowserSession: vi.fn(async () => undefined),
}));

const OFFICER_NAVIGATION = [
  "Home",
  "New Report",
  "Reports",
  "Policy Expert",
  "Forms Library",
  "Account",
];

const PRIMARY_ACTIONS = [
  "New Incident Report",
  "Open Count Sheet",
  "Ask a Policy Question",
  "Open Forms Library",
];

const PROFILE: SessionProfile = {
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

function renderApp(path = "/", profile: SessionProfile = PROFILE, onAuthenticationChanged?: () => void) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App profile={profile} onAuthenticationChanged={onAuthenticationChanged} />
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  document.body.style.overflow = "";
});

describe("Guided Operations officer application", () => {
  it("routes / to the authorized data-backed Home instead of the dormant static Home", async () => {
    renderApp("/");

    expect(await screen.findByRole("heading", { name: "Quick Forms" })).toBeInTheDocument();
    expect(fetchOfficerHomeSummary).toHaveBeenCalled();
    expect(screen.queryByRole("heading", { name: "Frequently Used Forms" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Your Daily Checklist" })).toBeInTheDocument();
  });

  it("renders the approved six-item officer navigation", () => {
    renderApp();

    const navigation = screen.getByRole("navigation", { name: "Officer navigation" });
    for (const label of OFFICER_NAVIGATION) {
      expect(within(navigation).getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(within(navigation).queryByText("Administration")).not.toBeInTheDocument();
  });

  it("uses the authenticated employee profile in the shell", () => {
    renderApp();

    expect(screen.getAllByText("Officer Casey Morgan").length).toBeGreaterThan(0);
    expect(screen.getAllByText("A Shift").length).toBeGreaterThan(0);
    expect(screen.getByText("CM")).toBeInTheDocument();
    expect(screen.queryByText("Officer Peterman")).not.toBeInTheDocument();
  });

  it("keeps the four primary daily actions easy to find", () => {
    renderApp();
    const actions = screen.getByRole("region", { name: "Primary actions" });

    for (const label of PRIMARY_ACTIONS) {
      expect(within(actions).getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(fetchOfficerHomeSummary).toHaveBeenCalled();
  });

  it("routes Policy Expert to the real citation workspace", () => {
    renderApp("/policy-expert");

    expect(screen.getByRole("heading", { name: "Policy Expert" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask Policy Expert" })).toBeInTheDocument();
    expect(screen.queryByText(/scheduled in the next product milestone/i)).not.toBeInTheDocument();
  });

  it("routes Forms Library to the real approved-form workspace", () => {
    renderApp("/forms");

    expect(screen.getByRole("heading", { name: "Forms Library" })).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: "Search forms" })).toBeInTheDocument();
    expect(screen.queryByText(/scheduled in the next product milestone/i)).not.toBeInTheDocument();
  });

  it("routes Account to the individual security workspace", () => {
    renderApp("/account");

    expect(screen.getByRole("heading", { name: "My Account" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Active browser sessions" })).toBeInTheDocument();
    expect(screen.queryByText(/scheduled in the next product milestone/i)).not.toBeInTheDocument();
  });

  it("exposes connection state without claiming fictional synchronization", () => {
    renderApp();

    expect(screen.getByText("Online")).toBeInTheDocument();
    expect(screen.getByText("Secure browser session")).toBeInTheDocument();
    expect(screen.queryByText(/Last synced 2 minutes ago/i)).not.toBeInTheDocument();
  });

  it("derives Online and Offline status from the browser connectivity signal", async () => {
    const online = vi.spyOn(window.navigator, "onLine", "get").mockReturnValue(true);
    renderApp();
    expect(screen.getByRole("status")).toHaveTextContent("Online");

    online.mockReturnValue(false);
    window.dispatchEvent(new Event("offline"));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Offline"));

    online.mockReturnValue(true);
    window.dispatchEvent(new Event("online"));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Online"));
    online.mockRestore();
  });

  it("provides a keyboard-operated profile menu with account and sign-out actions", async () => {
    const user = userEvent.setup();
    const authenticationChanged = vi.fn();
    renderApp("/", PROFILE, authenticationChanged);

    const trigger = screen.getByRole("button", { name: "Officer Casey Morgan" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");

    trigger.focus();
    await user.keyboard("{ArrowDown}");
    const account = await screen.findByRole("menuitem", { name: "Account and session" });
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    await waitFor(() => expect(account).toHaveFocus());
    expect(within(screen.getByRole("menu", { name: "Profile and session" })).getByText("A Shift")).toBeInTheDocument();
    expect(screen.getByText("Secure browser session", { selector: ".gow-profile-context span" })).toBeInTheDocument();

    await user.keyboard("{ArrowDown}");
    const signOut = screen.getByRole("menuitem", { name: "Sign out this device" });
    expect(signOut).toHaveFocus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(signOutCurrentBrowserSession).toHaveBeenCalledOnce());
    expect(authenticationChanged).toHaveBeenCalledOnce();
  });

  it("dismisses the profile menu with Escape and restores trigger focus", async () => {
    const user = userEvent.setup();
    renderApp();
    const trigger = screen.getByRole("button", { name: "Officer Casey Morgan" });
    await user.click(trigger);
    expect(screen.getByRole("menu", { name: "Profile and session" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu", { name: "Profile and session" })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("locks scrolling while the mobile drawer is open and restores focus when dismissed", async () => {
    const user = userEvent.setup();
    renderApp();
    const trigger = document.querySelector<HTMLButtonElement>(".gow-mobile-menu-trigger")!;
    trigger.style.display = "grid";
    const close = document.querySelector<HTMLButtonElement>(".gow-mobile-menu-button")!;
    close.style.display = "grid";
    await user.click(trigger);

    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(document.body.style.overflow).toBe("hidden");
    expect(close).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(document.body.style.overflow).toBe("");
    expect(trigger).toHaveFocus();
  });

  it("dismisses the mobile drawer from its scrim", async () => {
    const user = userEvent.setup();
    renderApp();
    const trigger = document.querySelector<HTMLButtonElement>(".gow-mobile-menu-trigger")!;
    trigger.style.display = "grid";
    await user.click(trigger);
    const scrim = document.querySelector<HTMLButtonElement>(".gow-mobile-scrim")!;
    scrim.style.display = "block";
    await user.click(scrim);
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(trigger).toHaveFocus();
  });
});
