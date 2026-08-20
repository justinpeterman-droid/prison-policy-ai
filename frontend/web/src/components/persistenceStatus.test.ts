import { describe, expect, it } from "vitest";
import { WebApiError } from "../api/client";
import {
  persistenceStateForError,
  persistenceStatusLabel,
  type PersistenceStatusState,
} from "./persistenceStatus";

describe("persistence status language", () => {
  it.each([
    ["loading", "Loading saved record…"],
    ["saved", "Saved to server"],
    ["saving", "Saving to server…"],
    ["unsaved", "Unsaved changes — server save pending"],
    ["reconnecting", "Reconnecting — changes remain visible; server save not confirmed"],
    ["offline", "Offline — changes remain visible; server save not confirmed"],
    ["conflict", "Save conflict — changes remain visible; server save not confirmed"],
    ["failed", "Save failed — changes remain visible; server save not confirmed"],
  ] satisfies Array<[PersistenceStatusState, string]>)("describes %s without overstating persistence", (state, label) => {
    expect(persistenceStatusLabel(state)).toBe(label);
  });

  it("classifies network, revision-conflict, and terminal save failures", () => {
    expect(persistenceStateForError(new WebApiError({
      status: 0,
      code: "network_unavailable",
      message: "Network unavailable",
    }))).toBe("reconnecting");
    expect(persistenceStateForError(new WebApiError({
      status: 409,
      code: "revision_conflict",
      message: "Revision conflict",
    }))).toBe("conflict");
    expect(persistenceStateForError(new WebApiError({
      status: 409,
      code: "request_in_progress",
      message: "A prior request is still running",
    }))).toBe("failed");
    expect(persistenceStateForError(new Error("Invalid form"))).toBe("failed");
  });
});
