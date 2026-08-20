import { WebApiError } from "../../../../api/client";
import type { EditorSaveState } from "./SaveState";

export function saveStateForError(reason: unknown): Extract<EditorSaveState, "reconnecting" | "failed"> {
  return reason instanceof WebApiError
    && (reason.status === 0 || reason.code === "network_unavailable")
    ? "reconnecting"
    : "failed";
}
