export type PersistenceStatusState =
  | "loading"
  | "saved"
  | "saving"
  | "unsaved"
  | "reconnecting"
  | "offline"
  | "conflict"
  | "failed";

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
