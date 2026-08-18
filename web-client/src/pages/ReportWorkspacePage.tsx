import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download, LoaderCircle, Save } from "lucide-react";
import { Button, Notice, PageHeader } from "../components/ui";
import { DraftStep, ReviewStep } from "../features/report-workspace/DraftReviewSteps";
import { NotesStep, FactsStep } from "../features/report-workspace/NotesFactsSteps";
import { ReportContext } from "../features/report-workspace/ReportContext";
import { WorkflowRail } from "../features/report-workspace/WorkflowRail";
import { useReportWorkspace } from "../features/report-workspace/useReportWorkspace";

export function ReportWorkspacePage() {
  const { reportId } = useParams();
  const workspace = useReportWorkspace(reportId);

  if (workspace.loading) {
    return (
      <div className="workspace-loading">
        <LoaderCircle className="spin" aria-hidden="true" />
        <span>Opening report workspace</span>
      </div>
    );
  }

  if (workspace.loadError) {
    return (
      <div className="page-stack report-workspace-page">
        <PageHeader
          eyebrow="Report workspace"
          title="Report unavailable"
          description="The requested report was not loaded, so no report content is displayed."
          actions={
            <Link className="button button--secondary button--md" to="/reports">
              <ArrowLeft aria-hidden="true" /><span>Back to reports</span>
            </Link>
          }
        />
        <Notice tone="danger" title="The report could not be opened">{workspace.loadError}</Notice>
      </div>
    );
  }

  const {
    isNew,
    report,
    setReport,
    step,
    setStep,
    narrative,
    setNarrative,
    fieldNotes,
    setFieldNotes,
    saving,
    job,
    message,
    currentStepIndex,
    changed,
    warnings,
    nextStep,
    save,
    generate,
    runExport,
  } = workspace;

  return (
    <div className="page-stack report-workspace-page">
      <PageHeader
        eyebrow={isNew ? "New report" : `Report …${report.reportId.slice(-8)}`}
        title={isNew ? "Create an incident report" : report.category ?? report.reportType}
        description={isNew ? "Begin with direct field notes. The assistant will organize only what you provide." : `${report.reportType} · Revision ${report.currentRevisionNumber} · Last edited by ${report.lastEditorDisplayName}`}
        actions={
          <div className="button-row">
            <Link className="button button--secondary button--md" to="/reports"><ArrowLeft aria-hidden="true" /><span>Back to reports</span></Link>
            <Button variant="secondary" onClick={() => void runExport()} icon={<Download aria-hidden="true" />}>Export revision</Button>
            <Button onClick={() => void save()} disabled={!changed || saving} icon={<Save aria-hidden="true" />}>{saving ? "Saving…" : "Save draft"}</Button>
          </div>
        }
      />

      {message ? <Notice tone={message.tone}>{message.text}</Notice> : null}

      <div className="report-workspace">
        <WorkflowRail step={step} currentStepIndex={currentStepIndex} onStep={setStep} />
        <section className="workspace-editor">
          {step === "notes" ? (
            <NotesStep fieldNotes={fieldNotes} setFieldNotes={setFieldNotes} saving={saving} onSave={save} onNext={nextStep} />
          ) : null}
          {step === "facts" ? (
            <FactsStep report={report} setReport={setReport} onBack={() => setStep("notes")} onGenerate={generate} />
          ) : null}
          {step === "draft" ? (
            <DraftStep narrative={narrative} setNarrative={setNarrative} job={job} onBack={() => setStep("facts")} onGenerate={generate} onNext={() => setStep("review")} />
          ) : null}
          {step === "review" ? (
            <ReviewStep report={report} narrative={narrative} warnings={warnings} changed={changed} saving={saving} onBack={() => setStep("draft")} onExport={runExport} onSave={save} />
          ) : null}
        </section>
        <ReportContext report={report} warnings={warnings} />
      </div>
    </div>
  );
}
