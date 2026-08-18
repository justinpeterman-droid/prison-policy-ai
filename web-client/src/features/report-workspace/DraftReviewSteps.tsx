import {
  AlertTriangle,
  ArrowLeft,
  BookOpenCheck,
  CheckCircle2,
  ChevronRight,
  Download,
  FileCheck2,
  LoaderCircle,
  RotateCcw,
  Save,
} from "lucide-react";
import { Button, Notice, ProgressBar } from "../../components/ui";
import type { JobSummary, ReportDetail } from "../../types";

export function DraftStep({
  narrative,
  setNarrative,
  job,
  onBack,
  onGenerate,
  onNext,
}: {
  narrative: string;
  setNarrative(value: string): void;
  job: JobSummary | null;
  onBack(): void;
  onGenerate(): Promise<void>;
  onNext(): void;
}) {
  return (
    <div className="editor-panel editor-panel--narrative">
      <div className="editor-panel__header">
        <div><p className="eyebrow">Step 3</p><h2>Draft narrative</h2><p>Revise the draft so it accurately reflects your documented facts.</p></div>
        <span className="character-count">{narrative.length.toLocaleString()} / 30,000</span>
      </div>
      {job?.state === "running" ? (
        <div className="generation-state"><LoaderCircle className="spin" aria-hidden="true" /><div><strong>{job.stage}</strong><ProgressBar value={64} label="Generation progress" /></div></div>
      ) : null}
      <label className="field field--editor narrative-editor">
        <span className="sr-only">Report narrative</span>
        <textarea value={narrative} onChange={(event) => setNarrative(event.target.value.slice(0, 30_000))} rows={20} placeholder="The generated draft will appear here for review." />
      </label>
      <div className="editor-actions">
        <Button variant="secondary" onClick={onBack} icon={<ArrowLeft aria-hidden="true" />}>Back</Button>
        <Button variant="secondary" onClick={() => void onGenerate()} icon={<RotateCcw aria-hidden="true" />}>Regenerate</Button>
        <Button onClick={onNext} disabled={!narrative.trim()}>Review report <ChevronRight aria-hidden="true" /></Button>
      </div>
    </div>
  );
}

export function ReviewStep({
  report,
  narrative,
  warnings,
  changed,
  saving,
  onBack,
  onExport,
  onSave,
}: {
  report: ReportDetail;
  narrative: string;
  warnings: string[];
  changed: boolean;
  saving: boolean;
  onBack(): void;
  onExport(): Promise<void>;
  onSave(): Promise<void>;
}) {
  return (
    <div className="editor-panel">
      <div className="editor-panel__header">
        <div><p className="eyebrow">Step 4</p><h2>Final review</h2><p>Resolve warnings, confirm authorship, then save or export a concrete revision.</p></div>
        <FileCheck2 aria-hidden="true" className="panel-heading-icon" />
      </div>
      <div className="review-summary">
        <div><span>Report type</span><strong>{report.reportType}</strong></div>
        <div><span>Current revision</span><strong>{report.currentRevisionNumber || "Not saved"}</strong></div>
        <div><span>Incident category</span><strong>{report.category || "Not selected"}</strong></div>
        <div><span>Narrative length</span><strong>{narrative.length.toLocaleString()} characters</strong></div>
      </div>
      <div className="review-validation">
        <h3>Review checks</h3>
        <ul>
          <li className="pass"><CheckCircle2 aria-hidden="true" /><span><strong>Chronology</strong><small>Sequence reads clearly from observation through disposition.</small></span></li>
          <li className={warnings.length ? "warning" : "pass"}>{warnings.length ? <AlertTriangle aria-hidden="true" /> : <CheckCircle2 aria-hidden="true" />}<span><strong>Required details</strong><small>{warnings.length ? `${warnings.length} item${warnings.length === 1 ? "" : "s"} need review.` : "No unresolved warnings."}</small></span></li>
          <li className="pass"><BookOpenCheck aria-hidden="true" /><span><strong>Policy support</strong><small>Review cited policy separately when procedure is material.</small></span></li>
        </ul>
      </div>
      {warnings.length ? (
        <Notice tone="warning" title="Resolve before completion"><ul className="notice-list">{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></Notice>
      ) : (
        <Notice tone="success" title="Ready for final action">Your report has no unresolved automated warnings. You remain responsible for the final content.</Notice>
      )}
      <div className="editor-actions">
        <Button variant="secondary" onClick={onBack} icon={<ArrowLeft aria-hidden="true" />}>Back to draft</Button>
        <Button variant="secondary" onClick={() => void onExport()} icon={<Download aria-hidden="true" />}>Export DOCX</Button>
        <Button onClick={() => void onSave()} disabled={!changed || saving} icon={<Save aria-hidden="true" />}>Save final review</Button>
      </div>
    </div>
  );
}
