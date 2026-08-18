import type { Dispatch, SetStateAction } from "react";
import { ArrowLeft, ChevronRight, Info, Save, Sparkles } from "lucide-react";
import { Button, Notice, StatusBadge } from "../../components/ui";
import type { ReportDetail } from "../../types";

export function NotesStep({
  fieldNotes,
  setFieldNotes,
  saving,
  onSave,
  onNext,
}: {
  fieldNotes: string;
  setFieldNotes(value: string): void;
  saving: boolean;
  onSave(): Promise<void>;
  onNext(): void;
}) {
  return (
    <div className="editor-panel">
      <div className="editor-panel__header">
        <div><p className="eyebrow">Step 1</p><h2>Field notes</h2><p>Paste or type direct observations, approximate times, identifiers, and notifications.</p></div>
        <span className="character-count">{fieldNotes.length.toLocaleString()} / 30,000</span>
      </div>
      <label className="field field--editor">
        <span className="sr-only">Field notes</span>
        <textarea
          value={fieldNotes}
          onChange={(event) => setFieldNotes(event.target.value.slice(0, 30_000))}
          placeholder="Example: At approx. 1840 hrs during routine inspection of Barracks 2, I observed…"
          rows={18}
        />
      </label>
      <div className="editor-guidance">
        <Info aria-hidden="true" />
        <span>Include only information relevant to the incident. Label estimates and attribute statements to their source.</span>
      </div>
      <div className="editor-actions">
        <Button variant="secondary" onClick={() => void onSave()} disabled={!fieldNotes.trim() || saving} icon={<Save aria-hidden="true" />}>Save notes</Button>
        <Button onClick={onNext} disabled={!fieldNotes.trim()}>Continue to details <ChevronRight aria-hidden="true" /></Button>
      </div>
    </div>
  );
}

export function FactsStep({
  report,
  setReport,
  onBack,
  onGenerate,
}: {
  report: ReportDetail;
  setReport: Dispatch<SetStateAction<ReportDetail>>;
  onBack(): void;
  onGenerate(): Promise<void>;
}) {
  const updateField = (key: string, value: string) => {
    setReport((current) => ({
      ...current,
      content: {
        ...current.content,
        editableFields: { ...current.content.editableFields, [key]: value },
      },
    }));
  };

  return (
    <div className="editor-panel">
      <div className="editor-panel__header">
        <div><p className="eyebrow">Step 2</p><h2>Incident details</h2><p>Verify extracted fields before requesting a narrative.</p></div>
        <StatusBadge status="in_progress" />
      </div>
      <div className="form-grid">
        <label className="field"><span>Incident date</span><input type="date" value={String(report.content.editableFields.incident_date ?? "")} onChange={(event) => updateField("incident_date", event.target.value)} /></label>
        <label className="field"><span>Approximate time</span><input type="time" value={String(report.content.editableFields.incident_time ?? "")} onChange={(event) => updateField("incident_time", event.target.value)} /></label>
        <label className="field"><span>Facility</span><input value={String(report.content.editableFields.facility ?? "")} onChange={(event) => updateField("facility", event.target.value)} placeholder="Facility or unit" /></label>
        <label className="field"><span>Location</span><input value={String(report.content.editableFields.location ?? "")} onChange={(event) => updateField("location", event.target.value)} placeholder="Specific incident location" /></label>
        <label className="field field--wide"><span>Category</span><select value={report.category ?? ""} onChange={(event) => setReport((current) => ({ ...current, category: event.target.value }))}><option value="">Select category</option><option>Contraband</option><option>Use of Force</option><option>Medical Response</option><option>Rule Violation</option><option>Other</option></select></label>
      </div>
      <Notice tone="info" title="Review before generation">Missing or uncertain details remain visible. The assistant will not silently fill them.</Notice>
      <div className="editor-actions">
        <Button variant="secondary" onClick={onBack} icon={<ArrowLeft aria-hidden="true" />}>Back</Button>
        <Button onClick={() => void onGenerate()} icon={<Sparkles aria-hidden="true" />}>Generate draft</Button>
      </div>
    </div>
  );
}
