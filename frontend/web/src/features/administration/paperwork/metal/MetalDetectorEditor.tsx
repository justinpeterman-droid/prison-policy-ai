import { useRef, useState } from "react";
import type { AdminStaffMember } from "../../api";
import { createDailyRecord, recordDailyAction, saveDailyRecord, type DailyRecord } from "../api";
import { StaffPicker } from "../roster/StaffPicker";
import { DailyEditorHeader } from "../shared/DailyEditorHeader";
import type { EditorSaveState } from "../shared/SaveState";
import { MetalDetectorPrint } from "./MetalDetectorPrint";
import { createEmptyMetalPayload, detectorMissingCorrectiveAction, DETECTOR_CODES, DETECTOR_POSITIONS, parseMetalPayload, type DetectorResult, type MetalPayload } from "./model";
import "./metal.css";


interface MetalDetectorEditorProps {
  workDate: string;
  shift: string;
  record: DailyRecord | null;
  onRecordChange: (record: DailyRecord) => void;
  searchStaff?: (query: string) => Promise<AdminStaffMember[]>;
}

export function MetalDetectorEditor({ workDate, shift, record, onRecordChange, searchStaff }: MetalDetectorEditorProps) {
  const [payload, setPayload] = useState<MetalPayload>(record ? parseMetalPayload(record.payload) : createEmptyMetalPayload(workDate, shift));
  const [saveState, setSaveState] = useState<EditorSaveState>(record ? "saved" : "unsaved");
  const [error, setError] = useState<string | null>(null);
  const [mobileDetector, setMobileDetector] = useState("1");
  const [previewOpen, setPreviewOpen] = useState(false);
  const correctiveRefs = useRef<Record<string, HTMLTextAreaElement | null>>({});

  function updateResult(detectorIndex: number, positionIndex: number, result: DetectorResult | null) {
    setPayload((current) => ({ ...current, detectors: current.detectors.map((detector, index) => index !== detectorIndex ? detector : { ...detector, tests: detector.tests.map((test, testIndex) => testIndex === positionIndex ? { ...test, result } : test) }) }));
    setSaveState("unsaved");
    setError(null);
  }

  function markDetectorPass(detectorIndex: number) {
    setPayload((current) => ({ ...current, detectors: current.detectors.map((detector, index) => index !== detectorIndex ? detector : { ...detector, tests: detector.tests.map((test) => test.result === null ? { ...test, result: "P" } : test) }) }));
    setSaveState("unsaved");
  }

  function navigateCell(event: React.KeyboardEvent<HTMLSelectElement>, detectorIndex: number, positionIndex: number) {
    const offsets: Record<string, [number, number]> = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowDown: [0, 1], ArrowUp: [0, -1] };
    const offset = offsets[event.key];
    if (!offset) return;
    const nextDetector = detectorIndex + offset[0];
    const nextPosition = positionIndex + offset[1];
    if (nextDetector < 0 || nextDetector >= 11 || nextPosition < 0 || nextPosition >= 7) return;
    event.preventDefault();
    document.getElementById(`metal-cell-${nextDetector}-${nextPosition}`)?.focus();
  }

  async function save() {
    const missing = detectorMissingCorrectiveAction(payload);
    if (missing) {
      setSaveState("failed");
      setError(`Detector ${missing.detector_code} has a failed test and requires corrective action before saving.`);
      correctiveRefs.current[missing.detector_code]?.focus();
      return;
    }
    setError(null);
    setSaveState("saving");
    try {
      const saved = record ? await saveDailyRecord({ kind: "metal_detector_test", recordId: record.recordId, workDate, shift, revision: record.revision, payload, reason: "manual_save" }) : await createDailyRecord({ kind: "metal_detector_test", workDate, shift, payload });
      setPayload(parseMetalPayload(saved.payload));
      setSaveState("saved");
      onRecordChange(saved);
    } catch (reason) {
      setSaveState("failed");
      setError(reason instanceof Error ? reason.message : "The detector test could not be saved.");
    }
  }

  async function preview() { if (record) await recordDailyAction("metal_detector_test", record.recordId, "preview"); setPreviewOpen(true); }
  async function print() { if (record) await recordDailyAction("metal_detector_test", record.recordId, "print"); window.print(); }

  const selectedMobile = payload.detectors[Number(mobileDetector) - 1];
  return <div className="metal-workspace">
    <DailyEditorHeader title="Daily Walk-Through Metal Detector Testing" workDate={workDate} shift={shift} saveState={saveState} onSave={() => void save()} onPreview={() => void preview()} onPrint={() => void print()} saveLabel="Save detector test" />
    {error ? <div className="admin-alert error" role="alert">{error}</div> : null}
    <section className="metal-signoff-card"><label>Tested by<StaffPicker label="Tested by" value={payload.tested_by} state={payload.tested_by ? "assigned" : "unassigned"} onChange={(tested_by) => { setPayload((current) => ({ ...current, tested_by })); setSaveState("unsaved"); }} searchStaff={searchStaff} /></label><label>Reviewed by<StaffPicker label="Reviewed by" value={payload.reviewed_by} state={payload.reviewed_by ? "assigned" : "unassigned"} onChange={(reviewed_by) => { setPayload((current) => ({ ...current, reviewed_by })); setSaveState("unsaved"); }} searchStaff={searchStaff} /></label></section>
    <section className="metal-matrix-card"><div className="metal-matrix-heading"><div><p>Seven-position functional test</p><h2>Detector matrix</h2></div><div>{DETECTOR_CODES.map((code, index) => <button key={code} type="button" aria-label={`Mark Detector ${code} Pass`} onClick={() => markDetectorPass(index)}>Detector {code} · P</button>)}</div></div><div className="metal-table-wrap"><table aria-label="Detector test matrix"><thead><tr><th>Test position</th>{DETECTOR_CODES.map((code) => <th key={code}>{code}</th>)}</tr></thead><tbody>{DETECTOR_POSITIONS.map((position, positionIndex) => <tr key={position}><th scope="row">{position}</th>{payload.detectors.map((detector, detectorIndex) => <td key={detector.detector_code}><select id={`metal-cell-${detectorIndex}-${positionIndex}`} aria-label={`Detector ${detector.detector_code} Position ${positionIndex + 1}`} value={detector.tests[positionIndex].result ?? ""} onChange={(event) => updateResult(detectorIndex, positionIndex, (event.target.value || null) as DetectorResult | null)} onKeyDown={(event) => navigateCell(event, detectorIndex, positionIndex)} onBlur={(event) => { if (event.currentTarget.value === "F") correctiveRefs.current[detector.detector_code]?.focus(); }}><option value="">—</option><option value="P">P</option><option value="F">F</option></select></td>)}</tr>)}</tbody></table></div></section>
    <section className="metal-mobile-editor"><label>Detector<select aria-label="Mobile detector" value={mobileDetector} onChange={(event) => setMobileDetector(event.target.value)}>{DETECTOR_CODES.map((code) => <option key={code} value={code}>Detector {code}</option>)}</select></label>{DETECTOR_POSITIONS.map((position, index) => <label key={position}>{position}<select aria-label={`Mobile Detector ${selectedMobile.detector_code} Position ${index + 1}`} value={selectedMobile.tests[index].result ?? ""} onChange={(event) => updateResult(Number(mobileDetector) - 1, index, (event.target.value || null) as DetectorResult | null)}><option value="">—</option><option value="P">Pass</option><option value="F">Fail</option></select></label>)}</section>
    <section className="metal-detail-grid">{payload.detectors.map((detector, index) => <article key={detector.detector_code} className={detector.tests.some((test) => test.result === "F") ? "has-failure" : ""}><h2>Detector {detector.detector_code}</h2><label>Location<input aria-label={`Detector ${detector.detector_code} location`} value={detector.location} maxLength={160} onChange={(event) => { setPayload((current) => ({ ...current, detectors: current.detectors.map((item, itemIndex) => itemIndex === index ? { ...item, location: event.target.value } : item) })); setSaveState("unsaved"); }} /></label><label>Equipment identifier<input aria-label={`Detector ${detector.detector_code} equipment identifier`} value={detector.equipment_identifier} maxLength={160} onChange={(event) => { setPayload((current) => ({ ...current, detectors: current.detectors.map((item, itemIndex) => itemIndex === index ? { ...item, equipment_identifier: event.target.value } : item) })); setSaveState("unsaved"); }} /></label><label>Corrective action<textarea ref={(element) => { correctiveRefs.current[detector.detector_code] = element; }} aria-label={`Detector ${detector.detector_code} corrective action`} value={detector.corrective_action} maxLength={2000} onChange={(event) => { setPayload((current) => ({ ...current, detectors: current.detectors.map((item, itemIndex) => itemIndex === index ? { ...item, corrective_action: event.target.value } : item) })); setSaveState("unsaved"); setError(null); }} /></label></article>)}</section>
    <section className="metal-comments-card"><label>Overall comments<textarea value={payload.comments} maxLength={10000} onChange={(event) => { setPayload((current) => ({ ...current, comments: event.target.value })); setSaveState("unsaved"); }} /></label></section>
    <MetalDetectorPrint payload={payload} />
    {previewOpen ? <div className="metal-preview-overlay" role="dialog" aria-modal="true" aria-label="Metal Detector Test print preview"><button type="button" onClick={() => setPreviewOpen(false)}>Close preview</button><MetalDetectorPrint payload={payload} /></div> : null}
  </div>;
}
