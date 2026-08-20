import { WebApiError } from "../api/client";

export type PersistenceStatusState =
  | "loading"
  | "saved"
  | "saving"
  | "unsaved"
  | "reconnecting"
  | "offline"
  | "conflict"
  | "failed";

export type PersistenceFailureState = Extract<
  PersistenceStatusState,
  "reconnecting" | "conflict" | "failed"
>;

const PERSISTENCE_STATUS_LABELS: Record<PersistenceStatusState, string> = {
  loading: "Loading saved record…",
  saved: "Saved to server",
  saving: "Saving to server…",
  unsaved: "Unsaved changes — server save pending",
  reconnecting: "Reconnecting — changes remain visible; server save not confirmed",
  offline: "Offline — changes remain visible; server save not confirmed",
  conflict: "Save conflict — changes remain visible; server save not confirmed",
  failed: "Save failed — changes remain visible; server save not confirmed",
};

export function persistenceStatusLabel(state: PersistenceStatusState): string {
  return PERSISTENCE_STATUS_LABELS[state];
}

export function persistenceStateForError(
  reason: unknown,
): PersistenceFailureState {
  if (!(reason instanceof WebApiError)) return "failed";
  if (reason.status === 0 || reason.code === "network_unavailable") return "reconnecting";
  if (reason.code === "revision_conflict" || reason.code === "idempotency_conflict") return "conflict";
  return "failed";
}

const PERSISTENCE_FAILURE_GUIDANCE: Record<PersistenceFailureState, string> = {
  reconnecting: "Entered work remains visible on this page. Server save not confirmed. Retry Save when the connection returns.",
  conflict: "Entered work remains visible on this page. Copy it, then reopen the latest server version before editing again.",
  failed: "Entered work remains visible on this page. Server save not confirmed. Use Retry Save when the issue is resolved.",
};

export function persistenceFailureGuidance(state: PersistenceFailureState): string {
  return PERSISTENCE_FAILURE_GUIDANCE[state];
}
