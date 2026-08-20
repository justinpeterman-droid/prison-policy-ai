import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { InterfaceIcon } from "../../../../components/InterfaceIcon";
import type { AdminStaffMember } from "../../api";
import {
  copyPreviousDailyRecord,
  createDailyRecord,
  recordDailyAction,
  saveDailyRecord,
  type DailyRecord,
} from "../api";
import { DailyEditorHeader } from "../shared/DailyEditorHeader";
import type { EditorSaveState } from "../shared/SaveState";
import { useDailyAutosave } from "../shared/useDailyAutosave";
import { AssignmentRosterPrint } from "./AssignmentRosterPrint";
import {
  createEmptyRosterPayload,
  parseRosterPayload,
  ROSTER_DEFINITION,
  type AssignmentState,
  type RosterPayload,
  type StaffSelection,
} from "./model";
import { StaffPicker } from "./StaffPicker";
import "./roster.css";


interface RosterEditorProps {
  workDate: string;
  shift: string;
  record: DailyRecord | null;
  onRecordChange: (record: DailyRecord) => void;
  searchStaff?: (query: string) => Promise<AdminStaffMember[]>;
}

interface LeaveDraft {
  staff: StaffSelection | null;
  leave_time: string;
  leave_type: string;
}

interface ExtraDraft {
  label: string;
  staff: StaffSelection | null;
}

const EQUIPMENT = [
  ["digital_camera", "Digital Camera"],
  ["video_camera_go_pro", "Video Camera (Go PRO)"],
  ["metal_detector_wands", "9 Metal Detector Wands"],
] as const;

function coverageCount(payload: RosterPayload): number {
  return payload.zones.reduce((count, zone) => {
    const definition = ROSTER_DEFINITION.zones.find((item) => item.code === zone.zone_code)!;
    return count + zone.posts.filter((assignment) => {
      const item = definition.posts.find((candidate) => candidate.code === assignment.post_code)!;
      return item.priority === "P1" && assignment.initial_staff === null;
    }).length;
  }, 0);
}

export function RosterEditor({ workDate, shift, record, onRecordChange, searchStaff }: RosterEditorProps) {
  const initial = record ? parseRosterPayload(record.payload) : createEmptyRosterPayload(workDate, shift);
  const [payload, setPayload] = useState<RosterPayload>(initial);
  const [leaveEntries, setLeaveEntries] = useState<LeaveDraft[]>(initial.leave_entries);
  const [extraAssignments, setExtraAssignments] = useState<ExtraDraft[]>(initial.extra_assignments);
  const [saveState, setSaveState] = useState<EditorSaveState>(record ? "saved" : "unsaved");
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [copyOpen, setCopyOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const dragged = useRef<{ zoneCode: string; postCode: string } | null>(null);
  const currentRecord = useRef(record);
  const draftVersion = useRef(0);
  const warningCount = coverageCount(payload);

  useLayoutEffect(() => {
    draftVersion.current += 1;
  }, [extraAssignments, leaveEntries, payload]);

  useEffect(() => {
    const current = currentRecord.current;
    if (record === null) {
      if (current === null) return;
      const empty = createEmptyRosterPayload(workDate, shift);
      currentRecord.current = null;
      setPayload(empty);
      setLeaveEntries(empty.leave_entries);
      setExtraAssignments(empty.extra_assignments);
      setSaveState("unsaved");
      setError(null);
      return;
    }
    if (current?.recordId === record.recordId && current.revision === record.revision) return;
    const loaded = parseRosterPayload(record.payload);
    currentRecord.current = record;
    setPayload(loaded);
    setLeaveEntries(loaded.leave_entries);
    setExtraAssignments(loaded.extra_assignments);
    setSaveState("saved");
    setError(null);
  }, [record, shift, workDate]);

  function updateSelection(
    zoneCode: string,
    postCode: string,
    column: "initial" | "rotation",
    staff: StaffSelection | null,
    state: AssignmentState,
  ) {
    setPayload((current) => ({
      ...current,
      zones: current.zones.map((zone) => zone.zone_code !== zoneCode ? zone : {
        ...zone,
        posts: zone.posts.map((post) => post.post_code !== postCode ? post : {
          ...post,
          [`${column}_staff`]: staff,
          [`${column}_state`]: state,
        }),
      }),
    }));
    setSaveState("unsaved");
  }

  function movePost(zoneCode: string, postCode: string, targetIndex: number) {
    setPayload((current) => ({
      ...current,
      zones: current.zones.map((zone) => {
        if (zone.zone_code !== zoneCode) return zone;
        const sourceIndex = zone.posts.findIndex((post) => post.post_code === postCode);
        if (sourceIndex < 0 || targetIndex < 0 || targetIndex >= zone.posts.length || sourceIndex === targetIndex) return zone;
        const posts = [...zone.posts];
        const [moved] = posts.splice(sourceIndex, 1);
        posts.splice(targetIndex, 0, moved);
        return { ...zone, posts };
      }),
    }));
    setSaveState("unsaved");
  }

  function staffField(label: string, value: StaffSelection | null, onChange: (staff: StaffSelection | null) => void) {
    return <StaffPicker label={label} value={value} state={value ? "assigned" : "unassigned"} onChange={(staff) => { onChange(staff); setSaveState("unsaved"); }} searchStaff={searchStaff} />;
  }

  function payloadForSave(): RosterPayload {
    return {
      ...payload,
      work_date: workDate,
      shift,
      leave_entries: leaveEntries.filter((entry): entry is LeaveDraft & { staff: StaffSelection } => entry.staff !== null),
      extra_assignments: extraAssignments.filter((entry) => entry.label.trim()).map((entry) => ({ ...entry, label: entry.label.trim() })),
    };
  }

  async function save(reason: "manual_save" | "autosave" = "manual_save") {
    setError(null);
    setSaveState("saving");
    const requestDraftVersion = draftVersion.current;
    try {
      const nextPayload = payloadForSave();
      const saved = currentRecord.current
        ? await saveDailyRecord({
          kind: "assignment_roster",
          recordId: currentRecord.current.recordId,
          workDate,
          shift,
          revision: currentRecord.current.revision,
          payload: nextPayload,
          reason,
        })
        : await createDailyRecord({ kind: "assignment_roster", workDate, shift, payload: nextPayload });
      currentRecord.current = saved;
      if (draftVersion.current === requestDraftVersion) {
        const savedPayload = parseRosterPayload(saved.payload);
        setPayload(savedPayload);
        setLeaveEntries(savedPayload.leave_entries);
        setExtraAssignments(savedPayload.extra_assignments);
        setSaveState("saved");
        setAnnouncement(`Roster saved as revision ${saved.revision}.`);
      } else {
        setSaveState("unsaved");
        setAnnouncement(`Revision ${saved.revision} saved. Newer edits remain unsaved.`);
      }
      onRecordChange(saved);
    } catch (reason) {
      setSaveState(draftVersion.current === requestDraftVersion ? "failed" : "unsaved");
      setError(reason instanceof Error ? reason.message : "The roster could not be saved.");
    }
  }

  useDailyAutosave({ enabled: Boolean(record), dirty: saveState === "unsaved", onSave: () => { void save("autosave"); } });

  async function copyPrevious() {
    setError(null);
    try {
      const copied = await copyPreviousDailyRecord("assignment_roster", workDate, shift);
      const copiedPayload = parseRosterPayload(copied.payload);
      currentRecord.current = copied;
      setPayload(copiedPayload);
      setLeaveEntries(copiedPayload.leave_entries);
      setExtraAssignments(copiedPayload.extra_assignments);
      setCopyOpen(false);
      setSaveState("saved");
      setAnnouncement(`Copied roster created for ${workDate}, ${shift} Shift.`);
      onRecordChange(copied);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The previous roster could not be copied.");
    }
  }

  async function preview() {
    if (record) await recordDailyAction("assignment_roster", record.recordId, "preview");
    setPreviewOpen(true);
  }

  async function print() {
    if (record) await recordDailyAction("assignment_roster", record.recordId, "print");
    window.print();
  }

  return (
    <div className="roster-workspace">
      <DailyEditorHeader title="Shift Assignment Roster" workDate={workDate} shift={shift} saveState={saveState} onSave={() => void save()} onPreview={() => void preview()} onPrint={() => void print()} saveLabel="Save roster" />
      <div className="roster-toolbar">
        <button type="button" className="admin-secondary-button" onClick={() => setCopyOpen(true)}>Copy previous roster</button>
        <span role="status" aria-label="Roster coverage" className={warningCount ? "roster-coverage has-warnings" : "roster-coverage"}>{warningCount ? `${warningCount} P1 posts need review` : "All P1 posts have initial assignments"}</span>
      </div>
      <div role="status" aria-label="Roster announcement" aria-live="polite" className="visually-hidden">{announcement}</div>
      {error ? <div className="admin-alert error" role="alert">{error}</div> : null}

      <section className="roster-command-card" aria-labelledby="roster-command-heading">
        <div className="roster-section-heading"><div><p>Shift personnel</p><h2 id="roster-command-heading">Command assignments</h2></div><span>Date {workDate} · {shift} Shift</span></div>
        <div className="roster-command-grid">
          <label>Captain{staffField("Captain", payload.captain, (captain) => setPayload((current) => ({ ...current, captain })))}</label>
          <label>Lieutenant{staffField("Lieutenant", payload.lieutenant, (lieutenant) => setPayload((current) => ({ ...current, lieutenant })))}</label>
          <label>Duty Warden<input value={payload.duty_warden ?? ""} onChange={(event) => { setPayload((current) => ({ ...current, duty_warden: event.target.value || null })); setSaveState("unsaved"); }} /></label>
          <label>Alternate Shift Supervisor{staffField("Alternate Shift Supervisor", payload.alternate_shift_supervisor, (alternate_shift_supervisor) => setPayload((current) => ({ ...current, alternate_shift_supervisor })))}</label>
        </div>
      </section>

      <div className="roster-zone-stack">
        {payload.zones.map((zone) => {
          const definition = ROSTER_DEFINITION.zones.find((item) => item.code === zone.zone_code)!;
          return (
            <section className="roster-zone-card" key={zone.zone_code} data-testid={`roster-zone-${zone.zone_code}`}>
              <div className="roster-zone-heading"><div><h2>{definition.label}</h2><p>{definition.area}</p></div><label>{definition.supervisor_label}{staffField(`${definition.label} supervisor`, zone.supervisor, (supervisor) => setPayload((current) => ({ ...current, zones: current.zones.map((item) => item.zone_code === zone.zone_code ? { ...item, supervisor } : item) })))}</label></div>
              <div className="roster-table-wrap">
                <table className="roster-assignment-table">
                  <thead><tr><th>Order</th><th>Priority / Post</th><th>Initial Officer</th><th>Rotation Officer</th></tr></thead>
                  <tbody>
                    {zone.posts.map((assignment, index) => {
                      const item = definition.posts.find((candidate) => candidate.code === assignment.post_code)!;
                      return (
                        <tr key={assignment.post_code} onDragOver={(event) => event.preventDefault()} onDrop={() => { const source = dragged.current; if (source?.zoneCode === zone.zone_code) movePost(zone.zone_code, source.postCode, index); dragged.current = null; }}>
                          <td><div className="roster-reorder-controls"><button type="button" draggable aria-label={`Drag ${item.label}`} onDragStart={() => { dragged.current = { zoneCode: zone.zone_code, postCode: assignment.post_code }; }}><InterfaceIcon name="drag" /></button><button type="button" aria-label={`Move ${item.label} up`} disabled={index === 0} onClick={() => movePost(zone.zone_code, assignment.post_code, index - 1)}><InterfaceIcon name="arrow-up" /></button><button type="button" aria-label={`Move ${item.label} down`} disabled={index === zone.posts.length - 1} onClick={() => movePost(zone.zone_code, assignment.post_code, index + 1)}><InterfaceIcon name="arrow-down" /></button></div></td>
                          <th scope="row"><span className={`roster-priority ${item.priority.toLowerCase()}`}>{item.priority}</span><span data-testid="roster-post-label">{item.label}</span></th>
                          <td><StaffPicker label={`${item.label} initial officer`} value={assignment.initial_staff} state={assignment.initial_state} onChange={(staff, state) => updateSelection(zone.zone_code, assignment.post_code, "initial", staff, state)} searchStaff={searchStaff} /></td>
                          <td><StaffPicker label={`${item.label} rotation officer`} value={assignment.rotation_staff} state={assignment.rotation_state} onChange={(staff, state) => updateSelection(zone.zone_code, assignment.post_code, "rotation", staff, state)} searchStaff={searchStaff} /></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          );
        })}
      </div>

      <div className="roster-operations-grid">
        <section className="roster-operation-card"><div className="roster-section-heading"><div><p>Personnel changes</p><h2>Leave entries</h2></div><button type="button" className="admin-text-button" onClick={() => { setLeaveEntries((items) => [...items, { staff: null, leave_time: "", leave_type: "" }]); setSaveState("unsaved"); }}>Add leave entry</button></div>{leaveEntries.map((entry, index) => <div className="roster-repeat-row" key={index}>{staffField(`Leave staff ${index + 1}`, entry.staff, (staff) => setLeaveEntries((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, staff } : item)))}<input aria-label={`Leave time ${index + 1}`} placeholder="Time" value={entry.leave_time} onChange={(event) => { setLeaveEntries((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, leave_time: event.target.value } : item)); setSaveState("unsaved"); }} /><input aria-label={`Leave type ${index + 1}`} placeholder="Type of leave" value={entry.leave_type} onChange={(event) => { setLeaveEntries((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, leave_type: event.target.value } : item)); setSaveState("unsaved"); }} /><button type="button" aria-label={`Remove leave entry ${index + 1}`} onClick={() => { setLeaveEntries((items) => items.filter((_, itemIndex) => itemIndex !== index)); setSaveState("unsaved"); }}><InterfaceIcon name="close" /></button></div>)}</section>
        <section className="roster-operation-card"><div className="roster-section-heading"><div><p>Additional duties</p><h2>Extra assignments</h2></div><button type="button" className="admin-text-button" onClick={() => { setExtraAssignments((items) => [...items, { label: "", staff: null }]); setSaveState("unsaved"); }}>Add extra assignment</button></div>{extraAssignments.map((entry, index) => <div className="roster-repeat-row" key={index}><input aria-label={`Extra assignment label ${index + 1}`} placeholder="Assignment" value={entry.label} onChange={(event) => { setExtraAssignments((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, label: event.target.value } : item)); setSaveState("unsaved"); }} />{staffField(`Extra assignment staff ${index + 1}`, entry.staff, (staff) => setExtraAssignments((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, staff } : item)))}<button type="button" aria-label={`Remove extra assignment ${index + 1}`} onClick={() => { setExtraAssignments((items) => items.filter((_, itemIndex) => itemIndex !== index)); setSaveState("unsaved"); }}><InterfaceIcon name="close" /></button></div>)}</section>
        <section className="roster-operation-card roster-briefing-card"><h2>Shift briefing</h2><label>Shift briefing minutes<textarea aria-label="Shift briefing minutes" value={payload.briefing_minutes} onChange={(event) => { setPayload((current) => ({ ...current, briefing_minutes: event.target.value })); setSaveState("unsaved"); }} /></label><label>Guests at Shift Briefing<input value={payload.briefing_guests.join(", ")} onChange={(event) => { setPayload((current) => ({ ...current, briefing_guests: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })); setSaveState("unsaved"); }} /></label></section>
        <section className="roster-operation-card"><h2>Security equipment</h2>{EQUIPMENT.map(([key, label]) => <label key={key}>{label}<select aria-label={label} value={payload.equipment[key]} onChange={(event) => { setPayload((current) => ({ ...current, equipment: { ...current.equipment, [key]: event.target.value as RosterPayload["equipment"][typeof key] } })); setSaveState("unsaved"); }}><option value="not_checked">Not checked</option><option value="yes">Accounted for</option><option value="no">Not accounted for</option></select></label>)}</section>
        <section className="roster-operation-card roster-checks"><h2>Completion and sign-off</h2><label><input aria-label="Roll call completed" type="checkbox" checked={payload.roll_call_completed} onChange={(event) => { setPayload((current) => ({ ...current, roll_call_completed: event.target.checked })); setSaveState("unsaved"); }} />Roll call completed</label><label><input type="checkbox" checked={payload.uniform_inspection_completed} onChange={(event) => { setPayload((current) => ({ ...current, uniform_inspection_completed: event.target.checked })); setSaveState("unsaved"); }} />Uniform inspection completed</label><label><input type="checkbox" checked={payload.assigned_and_dismissed} onChange={(event) => { setPayload((current) => ({ ...current, assigned_and_dismissed: event.target.checked })); setSaveState("unsaved"); }} />Assigned to post and dismissed</label><label>Lieutenant Signature<input value={payload.lieutenant_signature_name ?? ""} onChange={(event) => { setPayload((current) => ({ ...current, lieutenant_signature_name: event.target.value || null })); setSaveState("unsaved"); }} /></label></section>
      </div>

      <AssignmentRosterPrint payload={payloadForSave()} />
      {copyOpen ? <div className="admin-dialog-backdrop"><section role="dialog" aria-modal="true" aria-labelledby="copy-roster-title" className="admin-confirm-dialog"><h2 id="copy-roster-title">Copy previous roster</h2><p>The most recent {shift} Shift roster before {workDate} will be copied. Signatures, leave entries, briefing minutes, and completion checks are cleared; post assignments remain unchanged.</p><div><button type="button" className="admin-secondary-button" onClick={() => setCopyOpen(false)}>Cancel</button><button type="button" className="admin-primary-button" onClick={() => void copyPrevious()}>Create copied roster</button></div></section></div> : null}
      {previewOpen ? <div className="roster-preview-overlay" role="dialog" aria-modal="true" aria-label="Assignment Roster print preview"><button type="button" onClick={() => setPreviewOpen(false)}>Close preview</button><AssignmentRosterPrint payload={payloadForSave()} /></div> : null}
    </div>
  );
}
