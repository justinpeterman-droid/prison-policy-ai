import { useState } from "react";
import type { AdminStaffMember } from "../../api";
import {
  createDailyRecord,
  deriveUniformInspection,
  fetchDailyPaperwork,
  recordDailyAction,
  saveDailyRecord,
  type DailyRecord,
} from "../api";
import { StaffPicker } from "../roster/StaffPicker";
import { DailyEditorHeader } from "../shared/DailyEditorHeader";
import type { EditorSaveState } from "../shared/SaveState";
import {
  createEmptyUniformPayload,
  missingUniformComment,
  parseUniformPayload,
  UNIFORM_COLUMNS,
  UNIFORM_COLUMN_LABELS,
  UNIFORM_VALUES,
  type UniformPayload,
  type UniformValue,
} from "./model";
import { UniformInspectionPrint } from "./UniformInspectionPrint";
import "./uniform.css";


interface UniformInspectionEditorProps {
  workDate: string;
  shift: string;
  record: DailyRecord | null;
  onRecordChange: (record: DailyRecord) => void;
  searchStaff?: (query: string) => Promise<AdminStaffMember[]>;
}

export function UniformInspectionEditor({ workDate, shift, record, onRecordChange, searchStaff }: UniformInspectionEditorProps) {
  const [payload, setPayload] = useState<UniformPayload>(record ? parseUniformPayload(record.payload) : createEmptyUniformPayload(workDate, shift));
  const [saveState, setSaveState] = useState<EditorSaveState>(record ? "saved" : "unsaved");
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [importing, setImporting] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);

  function updateValue(staffId: string, column: (typeof UNIFORM_COLUMNS)[number], value: UniformValue | null) {
    setPayload((current) => ({ ...current, rows: current.rows.map((row) => row.staff.staff_id === staffId ? { ...row, [column]: value } : row) }));
    setSaveState("unsaved");
    setError(null);
  }

  function markColumnSatisfactory(column: (typeof UNIFORM_COLUMNS)[number]) {
    setPayload((current) => ({ ...current, rows: current.rows.map((row) => row[column] === null ? { ...row, [column]: "S" } : row) }));
    setSaveState("unsaved");
  }

  async function importRoster() {
    setError(null);
    setImporting(true);
    try {
      const page = await fetchDailyPaperwork(workDate, shift);
      const roster = page.items.find((item) => item.kind === "assignment_roster");
      if (!roster) throw new Error(`Save the ${workDate} ${shift} Shift Assignment Roster before importing staff.`);
      const derived = await deriveUniformInspection(roster.recordId, workDate, shift);
      setPayload(parseUniformPayload(derived.payload));
      setSaveState("saved");
      setAnnouncement(`Imported staff from Assignment Roster revision ${roster.revision}.`);
      onRecordChange(derived);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Roster staff could not be imported.");
    } finally {
      setImporting(false);
    }
  }

  async function save() {
    const missing = missingUniformComment(payload);
    if (missing) {
      setSaveState("failed");
      setError(`${missing.staff.display_name_snapshot} has an Unsatisfactory result and requires a comment before saving.`);
      return;
    }
    setError(null);
    setSaveState("saving");
    try {
      const saved = record
        ? await saveDailyRecord({ kind: "uniform_inspection", recordId: record.recordId, workDate, shift, revision: record.revision, payload, reason: "manual_save" })
        : await createDailyRecord({ kind: "uniform_inspection", workDate, shift, payload });
      setPayload(parseUniformPayload(saved.payload));
      setSaveState("saved");
      setAnnouncement(`Uniform Inspection saved as revision ${saved.revision}.`);
      onRecordChange(saved);
    } catch (reason) {
      setSaveState("failed");
      setError(reason instanceof Error ? reason.message : "The Uniform Inspection could not be saved.");
    }
  }

  async function preview() {
    if (record) await recordDailyAction("uniform_inspection", record.recordId, "preview");
    setPreviewOpen(true);
  }

  async function print() {
    if (record) await recordDailyAction("uniform_inspection", record.recordId, "print");
    window.print();
  }

  return (
    <div className="uniform-workspace">
      <DailyEditorHeader title="Uniform Inspection Log" workDate={workDate} shift={shift} saveState={saveState} onSave={() => void save()} onPreview={() => void preview()} onPrint={() => void print()} saveLabel="Save inspection" />
      <div className="uniform-toolbar">
        <button type="button" className="admin-secondary-button" onClick={() => void importRoster()} disabled={importing}>{importing ? "Importing roster staff…" : "Import staff from Assignment Roster"}</button>
        <span>{payload.roster_record_id ? `Roster revision ${payload.roster_revision_number}` : "No roster imported"}</span>
      </div>
      <div role="status" aria-live="polite" className="visually-hidden">{announcement}</div>
      {error ? <div className="admin-alert error" role="alert">{error}</div> : null}
      <section className="uniform-inspector-card"><div><p>Inspection responsibility</p><h2>Staff Conducting Inspection</h2></div><StaffPicker label="Staff Conducting Inspection" value={payload.inspector} state={payload.inspector ? "assigned" : "unassigned"} onChange={(inspector) => { setPayload((current) => ({ ...current, inspector })); setSaveState("unsaved"); }} searchStaff={searchStaff} /></section>
      <section className="uniform-matrix-card">
        <div className="uniform-bulk-bar"><div><p>Efficient entry</p><h2>Mark blank items satisfactory</h2></div><div>{UNIFORM_COLUMNS.map((column) => <button key={column} type="button" onClick={() => markColumnSatisfactory(column)} aria-label={`Mark ${UNIFORM_COLUMN_LABELS[column]} Satisfactory`}>{UNIFORM_COLUMN_LABELS[column]} · S</button>)}</div></div>
        {!payload.rows.length ? <div className="uniform-empty"><strong>No staff rows yet.</strong><p>Import the saved Assignment Roster to create one unique blank inspection row per assigned staff member.</p></div> : (
          <div className="uniform-table-wrap"><table aria-label="Uniform inspection matrix" className="uniform-matrix"><thead><tr><th>Name</th>{UNIFORM_COLUMNS.map((column) => <th key={column}>{UNIFORM_COLUMN_LABELS[column]}</th>)}<th>Comments</th></tr></thead><tbody>{payload.rows.map((row) => <tr key={row.staff.staff_id} className={UNIFORM_COLUMNS.some((column) => row[column] === "U") && !row.comments.trim() ? "needs-comment" : ""}><th scope="row">{row.staff.display_name_snapshot}</th>{UNIFORM_COLUMNS.map((column) => <td key={column}><select aria-label={`${row.staff.display_name_snapshot} ${UNIFORM_COLUMN_LABELS[column]}`} value={row[column] ?? ""} onChange={(event) => updateValue(row.staff.staff_id, column, (event.target.value || null) as UniformValue | null)}><option value="">—</option>{UNIFORM_VALUES.map((value) => <option key={value} value={value}>{value}</option>)}</select></td>)}<td><textarea aria-label={`${row.staff.display_name_snapshot} Comments`} value={row.comments} maxLength={500} onChange={(event) => { setPayload((current) => ({ ...current, rows: current.rows.map((item) => item.staff.staff_id === row.staff.staff_id ? { ...item, comments: event.target.value } : item) })); setSaveState("unsaved"); setError(null); }} /></td></tr>)}</tbody></table></div>
        )}
      </section>
      <UniformInspectionPrint payload={payload} />
      {previewOpen ? <div className="uniform-preview-overlay" role="dialog" aria-modal="true" aria-label="Uniform Inspection print preview"><button type="button" onClick={() => setPreviewOpen(false)}>Close preview</button><UniformInspectionPrint payload={payload} /></div> : null}
    </div>
  );
}
