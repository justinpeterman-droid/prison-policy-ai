import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, designPreviewEnabled } from "../../api/client";
import { previewReportDetail } from "../../data/preview";
import { exportReport, getReport, saveReport, submitJob } from "../reports/reportApi";
import type { JobSummary, ReportDetail } from "../../types";

export const reportSteps = [
  { id: "notes", label: "Field notes", description: "Document what was observed" },
  { id: "facts", label: "Incident details", description: "Verify extracted facts" },
  { id: "draft", label: "Draft narrative", description: "Review and revise language" },
  { id: "review", label: "Final review", description: "Resolve warnings and export" },
] as const;

export type ReportStepId = (typeof reportSteps)[number]["id"];
export type WorkspaceMessage = {
  tone: "success" | "warning" | "danger";
  text: string;
};

function blankReport(): ReportDetail {
  const now = new Date().toISOString();
  return {
    reportId: "new",
    incidentId: "new",
    reportType: "Incident Report",
    relationship: "owned",
    reportingOfficerDisplayName: "Current officer",
    preparerDisplayName: "Current officer",
    category: null,
    incidentDate: null,
    status: "in_progress",
    updatedAt: now,
    currentRevisionNumber: 0,
    lastEditorDisplayName: "Current officer",
    createdAt: now,
    content: {
      schemaVersion: 1,
      narrative: "",
      editableFields: {
        field_notes: "",
        facility: "",
        location: "",
        incident_date: "",
        incident_time: "",
      },
      validation: {},
      warnings: [],
    },
  };
}

export function useReportWorkspace(reportId?: string) {
  const navigate = useNavigate();
  const isNew = !reportId;
  const [report, setReport] = useState<ReportDetail>(() =>
    isNew || !designPreviewEnabled ? blankReport() : previewReportDetail,
  );
  const [step, setStep] = useState<ReportStepId>(isNew ? "notes" : "draft");
  const [narrative, setNarrative] = useState(report.content.narrative);
  const [fieldNotes, setFieldNotes] = useState(String(report.content.editableFields.field_notes ?? ""));
  const [loading, setLoading] = useState(!isNew && !designPreviewEnabled);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [job, setJob] = useState<JobSummary | null>(null);
  const [message, setMessage] = useState<WorkspaceMessage | null>(null);

  useEffect(() => {
    if (!reportId || designPreviewEnabled) return;
    let active = true;
    setLoading(true);
    setLoadError(null);
    getReport(reportId)
      .then((result) => {
        if (!active) return;
        setReport(result);
        setNarrative(result.content.narrative);
        setFieldNotes(String(result.content.editableFields.field_notes ?? ""));
      })
      .catch((cause) => {
        if (!active) return;
        setLoadError(cause instanceof ApiError ? cause.message : "The report could not be opened.");
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [reportId]);

  const currentStepIndex = reportSteps.findIndex((item) => item.id === step);
  const changed =
    narrative !== report.content.narrative ||
    fieldNotes !== String(report.content.editableFields.field_notes ?? "");
  const warnings = useMemo(() => {
    const items = [...report.content.warnings];
    if (!narrative.trim()) items.push("A narrative is required before final review.");
    if (!String(report.content.editableFields.location ?? "").trim()) {
      items.push("Confirm the incident location.");
    }
    return [...new Set(items)];
  }, [report, narrative]);

  const nextStep = () => {
    const next = reportSteps[Math.min(reportSteps.length - 1, currentStepIndex + 1)];
    setStep(next.id);
  };

  const save = async () => {
    setMessage(null);
    if (isNew && !designPreviewEnabled) {
      setMessage({
        tone: "warning",
        text: "The browser report-creation adapter is not connected yet. No report was saved.",
      });
      return;
    }
    setSaving(true);
    if (designPreviewEnabled) {
      await new Promise((resolve) => window.setTimeout(resolve, 450));
      const updated: ReportDetail = {
        ...report,
        reportId: isNew ? "00000000-0000-4000-8000-000000009001" : report.reportId,
        incidentId: isNew ? "00000000-0000-4000-8000-000000009002" : report.incidentId,
        currentRevisionNumber: report.currentRevisionNumber + 1,
        updatedAt: new Date().toISOString(),
        content: {
          ...report.content,
          narrative,
          editableFields: { ...report.content.editableFields, field_notes: fieldNotes },
        },
      };
      setReport(updated);
      setMessage({ tone: "success", text: `Draft saved as revision ${updated.currentRevisionNumber}.` });
      if (isNew) navigate(`/reports/${updated.reportId}`, { replace: true });
      setSaving(false);
      return;
    }
    try {
      const updated = await saveReport(
        {
          ...report,
          content: {
            ...report.content,
            editableFields: { ...report.content.editableFields, field_notes: fieldNotes },
          },
        },
        narrative,
      );
      setReport(updated);
      setNarrative(updated.content.narrative);
      setFieldNotes(String(updated.content.editableFields.field_notes ?? ""));
      setMessage({ tone: "success", text: `Draft saved as revision ${updated.currentRevisionNumber}.` });
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === "revision_conflict") {
        setMessage({
          tone: "warning",
          text: "A newer revision exists. Reload it and review the changes before saving again.",
        });
      } else {
        setMessage({
          tone: "danger",
          text: cause instanceof ApiError ? cause.message : "The report was not saved.",
        });
      }
    } finally {
      setSaving(false);
    }
  };

  const generate = async () => {
    setMessage(null);
    if (isNew && !designPreviewEnabled) {
      setMessage({ tone: "warning", text: "Save the incident workspace before requesting generation." });
      return;
    }
    if (designPreviewEnabled) {
      const previewJob: JobSummary = {
        id: crypto.randomUUID(),
        incidentId: report.incidentId,
        jobType: "generate",
        state: "running",
        stage: "Drafting narrative",
        createdAt: new Date().toISOString(),
        completedAt: null,
        errorCode: null,
      };
      setJob(previewJob);
      window.setTimeout(() => {
        setNarrative(previewReportDetail.content.narrative);
        setJob({
          ...previewJob,
          state: "succeeded",
          stage: "Draft ready",
          completedAt: new Date().toISOString(),
        });
        setMessage({
          tone: "success",
          text: "A draft is ready for your review. Verify every fact before saving.",
        });
        setStep("draft");
      }, 900);
      return;
    }
    try {
      setJob(await submitJob(report.incidentId, "generate", report.currentRevisionNumber));
      setMessage({
        tone: "success",
        text: "Generation was queued. This workspace will show the result when the job completes.",
      });
    } catch (cause) {
      setMessage({
        tone: "danger",
        text: cause instanceof ApiError ? cause.message : "Generation could not be started.",
      });
    }
  };

  const runExport = async () => {
    if (isNew || report.currentRevisionNumber < 1) {
      setMessage({ tone: "warning", text: "Save a revision before exporting." });
      return;
    }
    if (designPreviewEnabled) {
      setMessage({
        tone: "success",
        text: `Design preview: revision ${report.currentRevisionNumber} is ready for authorized DOCX export.`,
      });
      return;
    }
    try {
      await exportReport(report.reportId, report.currentRevisionNumber);
    } catch (cause) {
      setMessage({
        tone: "danger",
        text: cause instanceof ApiError ? cause.message : "The export could not be created.",
      });
    }
  };

  return {
    isNew,
    report,
    setReport,
    step,
    setStep,
    narrative,
    setNarrative,
    fieldNotes,
    setFieldNotes,
    loading,
    loadError,
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
  };
}
