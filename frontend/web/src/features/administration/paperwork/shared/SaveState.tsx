export type EditorSaveState = "saved" | "saving" | "unsaved" | "reconnecting" | "failed";


const LABELS: Record<EditorSaveState, string> = {
  saved: "Saved",
  saving: "Saving…",
  unsaved: "Unsaved changes",
  reconnecting: "Reconnecting…",
  failed: "Save failed—work preserved",
};


export function SaveState({ state }: { state: EditorSaveState }) {
  return <span className={`daily-save-state ${state}`} role="status">{LABELS[state]}</span>;
}
