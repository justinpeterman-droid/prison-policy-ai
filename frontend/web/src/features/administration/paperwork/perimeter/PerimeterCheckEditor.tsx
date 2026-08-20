import { useEffect, useState } from "react";
import type { AdminStaffMember } from "../../api";
import { createDailyRecord, fetchDailyTemplate, recordDailyAction, saveDailyRecord, type DailyRecord } from "../api";
import { StaffPicker } from "../roster/StaffPicker";
import { DailyEditorHeader } from "../shared/DailyEditorHeader";
import type { EditorSaveState } from "../shared/SaveState";
import { useDailyAutosave } from "../shared/useDailyAutosave";
import { createEmptyPerimeterPayload, parsePerimeterDefinition, parsePerimeterPayload, type PerimeterDefinition, type PerimeterPayload, type PerimeterResult } from "./model";
import { PerimeterCheckPrint } from "./PerimeterCheckPrint";
import "./perimeter.css";


interface PerimeterCheckEditorProps {
  workDate: string;
  shift: string;
  record: DailyRecord | null;
  onRecordChange: (record: DailyRecord) => void;
  searchStaff?: (query: string) => Promise<AdminStaffMember[]>;
}

export function PerimeterCheckEditor({ workDate, shift, record, onRecordChange, searchStaff }: PerimeterCheckEditorProps) {
  const initialDefinition = record ? parsePerimeterDefinition(record.template.definition) : null;
  const [definition, setDefinition] = useState<PerimeterDefinition | null>(initialDefinition);
  const [payload, setPayload] = useState<PerimeterPayload | null>(record && initialDefinition ? parsePerimeterPayload(record.payload, initialDefinition) : null);
  const [saveState, setSaveState] = useState<EditorSaveState>(record ? "saved" : "unsaved");
  const [error, setError] = useState<string | null>(null);
  const [warningOpen, setWarningOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);

  useEffect(() => {
    if (definition) return;
    let active = true;
    void fetchDailyTemplate("perimeter_check").then((template) => {
      if (!active) return;
      const nextDefinition = parsePerimeterDefinition(template.definition);
      setDefinition(nextDefinition);
      setPayload(createEmptyPerimeterPayload(workDate, shift, nextDefinition));
    }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "The perimeter definition could not be loaded."); });
    return () => { active = false; };
  }, [definition, shift, workDate]);

  useDailyAutosave({ enabled: Boolean(record), dirty: saveState === "unsaved", onSave: () => { void save("autosave"); } });

  if (!definition || !payload) return <div className="admin-loading-panel" aria-busy="true">Loading approved perimeter checks…</div>;

  const unchecked = payload.checks.filter((check) => check.result === null).length;
  const unsatisfactory = payload.checks.filter((check) => check.result === "U").length;
  const resultByCode = new Map(payload.checks.map((check) => [check.check_code, check.result]));

  function setResult(code: string, result: PerimeterResult | null) {
    setPayload((current) => current ? { ...current, checks: current.checks.map((check) => check.check_code === code ? { ...check, result } : check) } : current);
    setSaveState("unsaved");
  }

  function markGroup(groupCode: string) {
    const codes = new Set(definition!.groups.find((group) => group.code === groupCode)!.items.map((item) => item.code));
    setPayload((current) => current ? { ...current, checks: current.checks.map((check) => codes.has(check.check_code) && check.result === null ? { ...check, result: "S" } : check) } : current);
    setSaveState("unsaved");
  }

  async function save(reason: "manual_save" | "autosave" = "manual_save") {
    const submission = payload;
    if (!submission) return;
    setSaveState("saving"); setError(null);
    try {
      const saved = record ? await saveDailyRecord({ kind: "perimeter_check", recordId: record.recordId, workDate, shift, revision: record.revision, payload: submission, reason }) : await createDailyRecord({ kind: "perimeter_check", workDate, shift, payload: submission });
      setPayload(parsePerimeterPayload(saved.payload, definition!));
      setSaveState("saved"); onRecordChange(saved);
    } catch (reason) { setSaveState("failed"); setError(reason instanceof Error ? reason.message : "The perimeter check could not be saved."); }
  }

  async function showPreview() { if (record) await recordDailyAction("perimeter_check", record.recordId, "preview"); setWarningOpen(false); setPreviewOpen(true); }
  function preview() { if (unchecked) setWarningOpen(true); else void showPreview(); }
  async function print() { if (record) await recordDailyAction("perimeter_check", record.recordId, "print"); window.print(); }

  return <div className="perimeter-workspace">
    <DailyEditorHeader title="Perimeter Check List" workDate={workDate} shift={shift} saveState={saveState} onSave={() => void save()} onPreview={preview} onPrint={() => void print()} saveLabel="Save perimeter check" />
    <div role="status" aria-label="Perimeter completion summary" className="perimeter-summary"><span>{unchecked} unchecked</span><span>{unsatisfactory} unsatisfactory</span></div>
    {error ? <div className="admin-alert error" role="alert">{error}</div> : null}
    <div className="perimeter-groups">{definition.groups.map((group) => <details open key={group.code} role="group" aria-label={group.label} className="perimeter-group"><summary><span><strong>{group.label}</strong><small>{group.items.filter((item) => resultByCode.get(item.code) === null).length} unchecked · {group.items.filter((item) => resultByCode.get(item.code) === "U").length} U</small></span><button type="button" aria-label={`Mark ${group.label} Satisfactory`} onClick={(event) => { event.preventDefault(); markGroup(group.code); }}>Mark group S</button></summary><div>{group.items.map((item) => <label key={item.code} className={resultByCode.get(item.code) === "U" ? "is-unsatisfactory" : ""}><span>{item.label}</span><select aria-label={`${item.label} perimeter result`} value={resultByCode.get(item.code) ?? ""} onChange={(event) => setResult(item.code, (event.target.value || null) as PerimeterResult | null)}><option value="">—</option><option value="S">S</option><option value="U">U</option></select></label>)}</div></details>)}</div>
    <section className="perimeter-signoff"><label>Perimeter Inspected by<StaffPicker label="Perimeter Inspected by" value={payload.perimeter_inspector} state={payload.perimeter_inspector ? "assigned" : "unassigned"} onChange={(perimeter_inspector) => { setPayload((current) => current ? { ...current, perimeter_inspector } : current); setSaveState("unsaved"); }} searchStaff={searchStaff} /></label><label>Perimeter Signature<input aria-label="Perimeter Signature" value={payload.perimeter_signature_name ?? ""} onChange={(event) => { setPayload((current) => current ? { ...current, perimeter_signature_name: event.target.value || null } : current); setSaveState("unsaved"); }} /></label><label>Date / Time<input type="datetime-local" value={payload.perimeter_inspected_at ?? ""} onChange={(event) => { setPayload((current) => current ? { ...current, perimeter_inspected_at: event.target.value || null } : current); setSaveState("unsaved"); }} /></label><label>Senstar Inspected by<StaffPicker label="Senstar Inspected by" value={payload.senstar_inspector} state={payload.senstar_inspector ? "assigned" : "unassigned"} onChange={(senstar_inspector) => { setPayload((current) => current ? { ...current, senstar_inspector } : current); setSaveState("unsaved"); }} searchStaff={searchStaff} /></label><label>Shift Supervisor's Signature<input aria-label="Shift Supervisor's Signature" value={payload.supervisor_signature_name ?? ""} onChange={(event) => { setPayload((current) => current ? { ...current, supervisor_signature_name: event.target.value || null } : current); setSaveState("unsaved"); }} /></label><label>Date / Time<input type="datetime-local" value={payload.supervisor_signed_at ?? ""} onChange={(event) => { setPayload((current) => current ? { ...current, supervisor_signed_at: event.target.value || null } : current); setSaveState("unsaved"); }} /></label></section>
    <PerimeterCheckPrint payload={payload} definition={definition} />
    {warningOpen ? <div className="admin-dialog-backdrop"><section role="dialog" aria-modal="true" aria-label="Incomplete perimeter preview" className="admin-confirm-dialog"><h2>Incomplete perimeter preview</h2><p>{unchecked} unchecked perimeter items will print as blank. Review the checklist or continue with the visible incomplete state.</p><div><button type="button" className="admin-secondary-button" onClick={() => setWarningOpen(false)}>Return to checklist</button><button type="button" className="admin-primary-button" onClick={() => void showPreview()}>Continue to preview</button></div></section></div> : null}
    {previewOpen ? <div className="perimeter-preview-overlay" role="dialog" aria-modal="true" aria-label="Perimeter Check print preview"><button type="button" onClick={() => setPreviewOpen(false)}>Close preview</button><PerimeterCheckPrint payload={payload} definition={definition} /></div> : null}
  </div>;
}
