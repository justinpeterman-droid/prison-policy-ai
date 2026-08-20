import { describe, expect, it } from "vitest";
import { WebApiError } from "../../../../api/client";
import { saveStateForError } from "./saveStateForError";

describe("saveStateForError", () => {
  it("classifies an unreachable service as reconnecting", () => {
    expect(saveStateForError(new WebApiError({
      code: "network_unavailable",
      message: "The service could not be reached.",
      status: 0,
      retryable: true,
    }))).toBe("reconnecting");
  });

  it("keeps server and validation failures distinct", () => {
    expect(saveStateForError(new WebApiError({
      code: "dependency_unavailable",
      message: "A dependency is unavailable.",
      status: 503,
      retryable: true,
    }))).toBe("failed");
    expect(saveStateForError(new Error("Invalid form"))).toBe("failed");
  });

  it("preserves revision conflicts as an explicit recoverable state", () => {
    expect(saveStateForError(new WebApiError({
      code: "revision_conflict",
      message: "The record changed on the server.",
      status: 409,
      retryable: true,
    }))).toBe("conflict");
  });
});
