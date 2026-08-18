import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./AuthProvider";

function Probe() {
  const { status } = useAuth();
  return <span>{status}</span>;
}

describe("AuthProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers(),
      json: async () => ({ error: { code: "authentication_required", message: "Sign in.", retryable: false } }),
    }));
  });

  it("does not persist authentication credentials in browser storage", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByText(/signed-/i)).toBeVisible());
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
});
