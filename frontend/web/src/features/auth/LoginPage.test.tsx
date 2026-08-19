import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginPage } from "./LoginPage";

const signIn = vi.fn();

vi.mock("./AuthProvider", () => ({
  useAuth: () => ({
    status: "unauthenticated",
    profile: null,
    message: null,
    signIn,
    signOut: vi.fn(),
    refresh: vi.fn(),
  }),
}));

beforeEach(() => {
  signIn.mockReset();
  signIn.mockResolvedValue(undefined);
});

describe("LoginPage", () => {
  it("uses an approachable individual employee sign-in form", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", { name: "Sign in to continue" })).toBeInTheDocument();
    expect(screen.getByLabelText("Employee number")).toBeInTheDocument();
    expect(screen.getByLabelText("PIN")).toHaveAttribute("type", "password");
    expect(screen.getByLabelText("Keep me signed in on this device")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("submits only the employee number, PIN, and persistence choice", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.type(screen.getByLabelText("Employee number"), "F-1001");
    await user.type(screen.getByLabelText("PIN"), "0123");
    await user.click(screen.getByLabelText("Keep me signed in on this device"));
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(signIn).toHaveBeenCalledWith({
      employeeNumber: "F-1001",
      pin: "0123",
      persistent: true,
    });
  });
});
