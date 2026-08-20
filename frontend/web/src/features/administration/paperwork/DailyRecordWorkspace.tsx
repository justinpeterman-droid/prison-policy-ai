import { useEffect, useState } from "react";
import type { DailyPaperworkKind, DailyRecord } from "./api";
import { fetchDailyRecord } from "./api";
import { DAILY_CARD_DEFINITIONS } from "./DailyPaperworkTab";
import { DailyEditorHeader } from "./shared/DailyEditorHeader";


interface DailyRecordWorkspaceProps {
  kind: DailyPaperworkKind;
  recordId: string | null;
  workDate: string;
  shift: string;
}


export function DailyRecordWorkspace({ kind, recordId, workDate, shift }: DailyRecordWorkspaceProps) {
  const [record, setRecord] = useState<DailyRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const definition = DAILY_CARD_DEFINITIONS.find((item) => item.kind === kind);

  useEffect(() => {
    if (!recordId) return;
    let active = true;
    setError(null);
    void fetchDailyRecord(kind, recordId)
      .then((value) => { if (active) setRecord(value); })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "The saved daily record could not be opened.");
      });
    return () => { active = false; };
  }, [kind, recordId]);

  const title = record?.title ?? definition?.title ?? "Daily Paperwork";
  return (
    <div className="admin-page daily-editor-page">
      <DailyEditorHeader
        title={title}
        workDate={record?.workDate ?? workDate}
        shift={record?.shift ?? shift}
        saveState={record ? "saved" : "unsaved"}
      />
      {error ? <div className="admin-alert error" role="alert">{error}</div> : null}
      {recordId && !record && !error ? <div className="admin-loading-panel" aria-busy="true">Opening saved record…</div> : null}
      {!recordId ? (
        <section className="daily-editor-empty">
          <h2>Start {title}</h2>
          <p>The approved editor opens here after its form-specific fields are initialized. No record exists until the administrator saves it.</p>
        </section>
      ) : null}
      {record ? (
        <section className="daily-editor-empty">
          <h2>Revision {record.revision}</h2>
          <p>The saved record and approved template loaded successfully. Form-specific editing controls are available in the next implementation task.</p>
        </section>
      ) : null}
    </div>
  );
}
