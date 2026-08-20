import { lazy, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { DailyPaperworkKind, DailyRecord } from "./api";
import { fetchDailyRecord } from "./api";
import { DAILY_CARD_DEFINITIONS } from "./DailyPaperworkTab";
import { DailyEditorHeader } from "./shared/DailyEditorHeader";
import { DailyRevisionPanel } from "./shared/DailyRevisionPanel";

const RosterEditor = lazy(() => import("./roster/RosterEditor").then((module) => ({ default: module.RosterEditor })));
const UniformInspectionEditor = lazy(() => import("./uniform/UniformInspectionEditor").then((module) => ({ default: module.UniformInspectionEditor })));
const MetalDetectorEditor = lazy(() => import("./metal/MetalDetectorEditor").then((module) => ({ default: module.MetalDetectorEditor })));
const PerimeterCheckEditor = lazy(() => import("./perimeter/PerimeterCheckEditor").then((module) => ({ default: module.PerimeterCheckEditor })));
const RandomSearchesEditor = lazy(() => import("./searches/RandomSearchesEditor").then((module) => ({ default: module.RandomSearchesEditor })));
const DetectorSignOutEditor = lazy(() => import("./signout/DetectorSignOutEditor").then((module) => ({ default: module.DetectorSignOutEditor })));


interface DailyRecordWorkspaceProps {
  kind: DailyPaperworkKind;
  recordId: string | null;
  workDate: string;
  shift: string;
}


export function DailyRecordWorkspace({ kind, recordId, workDate, shift }: DailyRecordWorkspaceProps) {
  const [params, setParams] = useSearchParams();
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

  function acceptRecord(next: DailyRecord) {
    setRecord(next);
    if (params.get("record_id") === next.recordId) return;
    const updated = new URLSearchParams(params);
    updated.set("record_id", next.recordId);
    setParams(updated, { replace: true });
  }

  if (kind === "assignment_roster" && (!recordId || record)) {
    return (
      <div className="admin-page daily-editor-page">
        <Suspense fallback={<div className="admin-loading-panel" aria-busy="true">Loading Assignment Roster editor…</div>}><RosterEditor workDate={workDate} shift={shift} record={record} onRecordChange={acceptRecord} /></Suspense>
        {record ? <DailyRevisionPanel record={record} onRestored={acceptRecord} /> : null}
      </div>
    );
  }

  if (kind === "uniform_inspection" && (!recordId || record)) {
    return (
      <div className="admin-page daily-editor-page">
        <Suspense fallback={<div className="admin-loading-panel" aria-busy="true">Loading Uniform Inspection editor…</div>}><UniformInspectionEditor key={`${record?.recordId ?? "new"}-${record?.revision ?? 0}`} workDate={workDate} shift={shift} record={record} onRecordChange={acceptRecord} /></Suspense>
        {record ? <DailyRevisionPanel record={record} onRestored={acceptRecord} /> : null}
      </div>
    );
  }

  if (kind === "metal_detector_test" && (!recordId || record)) {
    return (
      <div className="admin-page daily-editor-page">
        <Suspense fallback={<div className="admin-loading-panel" aria-busy="true">Loading Metal Detector editor…</div>}><MetalDetectorEditor key={`${record?.recordId ?? "new"}-${record?.revision ?? 0}`} workDate={workDate} shift={shift} record={record} onRecordChange={acceptRecord} /></Suspense>
        {record ? <DailyRevisionPanel record={record} onRestored={acceptRecord} /> : null}
      </div>
    );
  }

  if (kind === "perimeter_check" && (!recordId || record)) {
    return (
      <div className="admin-page daily-editor-page">
        <Suspense fallback={<div className="admin-loading-panel" aria-busy="true">Loading Perimeter Check editor…</div>}><PerimeterCheckEditor key={`${record?.recordId ?? "new"}-${record?.revision ?? 0}`} workDate={workDate} shift={shift} record={record} onRecordChange={acceptRecord} /></Suspense>
        {record ? <DailyRevisionPanel record={record} onRestored={acceptRecord} /> : null}
      </div>
    );
  }

  if (kind === "random_search_log" && (!recordId || record)) {
    return <div className="admin-page daily-editor-page"><Suspense fallback={<div className="admin-loading-panel" aria-busy="true">Loading Random Searches editor…</div>}><RandomSearchesEditor key={`${record?.recordId ?? "new"}-${record?.revision ?? 0}`} workDate={workDate} shift={shift} record={record} onRecordChange={acceptRecord} /></Suspense>{record ? <DailyRevisionPanel record={record} onRestored={acceptRecord} /> : null}</div>;
  }

  if (kind === "detector_sign_out" && (!recordId || record)) {
    return <div className="admin-page daily-editor-page"><Suspense fallback={<div className="admin-loading-panel" aria-busy="true">Loading Detector Sign-Out editor…</div>}><DetectorSignOutEditor key={`${record?.recordId ?? "new"}-${record?.revision ?? 0}`} workDate={workDate} shift={shift} record={record} onRecordChange={acceptRecord} /></Suspense>{record ? <DailyRevisionPanel record={record} onRestored={acceptRecord} /> : null}</div>;
  }

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
