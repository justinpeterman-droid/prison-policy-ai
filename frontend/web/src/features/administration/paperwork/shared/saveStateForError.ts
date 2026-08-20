import { persistenceStateForError } from "../../../../components/persistenceStatus";
import type { EditorSaveState } from "./SaveState";

export function saveStateForError(reason: unknown): Extract<EditorSaveState, "reconnecting" | "conflict" | "failed"> {
  return persistenceStateForError(reason);
}
