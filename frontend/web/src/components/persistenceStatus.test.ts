import { describe, expect, it } from "vitest";
import { persistenceStatusLabel, type PersistenceStatusState } from "./persistenceStatus";

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
});
