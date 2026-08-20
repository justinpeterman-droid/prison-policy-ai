import { persistenceStatusLabel } from "../../../../components/persistenceStatus";

export type EditorSaveState = "saved" | "saving" | "unsaved" | "reconnecting" | "failed";

export function SaveState({ state }: { state: EditorSaveState }) {
  return (
    <span
      className={`daily-save-state ${state}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {persistenceStatusLabel(state)}
    </span>
  );
}
