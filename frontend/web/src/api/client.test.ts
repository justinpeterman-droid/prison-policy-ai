import { afterEach, describe, expect, it, vi } from "vitest";
import { WebApiError, webApiRequest } from "./client";

function response(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "X-Request-ID": "req-test" },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  document.cookie = "slut_web_csrf=; Max-Age=0; path=/";
});

describe("webApiRequest", () => {
  it("always uses same-origin cookies without exposing credentials", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({ data: { authenticated: false, profile: null } }),
    );

    await webApiRequest("/auth/session");

    const [, init] = fetchMock.mock.calls[0];
    expect(init?.credentials).toBe("include");
    expect(new Headers(init?.headers).get("X-Client-Version")).toBe("0.1.0");
    expect(new Headers(init?.headers).get("X-Request-ID")).toBeTruthy();
    expect(JSON.stringify(init)).not.toContain("access_token");
    expect(JSON.stringify(init)).not.toContain("renewal_token");
  });

  it("adds the readable CSRF cookie to modifying requests", async () => {
    document.cookie = "slut_web_csrf=csrf-value; path=/";
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({ data: { signed_out: true } }),
    );

    await webApiRequest("/auth/logout", { method: "POST" });

    const [, init] = fetchMock.mock.calls[0];
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("csrf-value");
  });

  it("does not require a preexisting CSRF cookie for login", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({ data: { authenticated: true, profile: {} } }),
    );

    await webApiRequest("/auth/login", { method: "POST", body: "{}" });

    const [, init] = fetchMock.mock.calls[0];
    expect(new Headers(init?.headers).has("X-CSRF-Token")).toBe(false);
  });

  it("maps safe server errors into a typed WebApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({
        error: {
          code: "invalid_credentials",
          message: "The employee number or PIN is incorrect.",
          retryable: false,
          details: {},
        },
        request_id: "req-invalid",
      }, 401),
    );

    await expect(webApiRequest("/auth/login", { method: "POST" })).rejects.toMatchObject({
      name: "WebApiError",
      code: "invalid_credentials",
      status: 401,
      requestId: "req-invalid",
    } satisfies Partial<WebApiError>);
  });

  it("preserves a clear retryable network error", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("offline"));

    await expect(webApiRequest("/auth/session")).rejects.toMatchObject({
      code: "network_unavailable",
      retryable: true,
      status: 0,
    });
  });
});
