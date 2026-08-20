import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { DocumentStudioPage } from "../../incidents/DocumentStudioPage";
import { listAdminStaff, type AdminStaffMember } from "../api";
import { AdminStepUpDialog } from "../AdminStepUpDialog";
import { AdminAttributionBanner } from "./AdminAttributionBanner";
import {
  changeAdminRecordsStatus,
  getAdminIncidentDetail,
  restoreAdminIncident,
  transferAdminReport,
  type AdminIncidentDetail,
} from "./api";

type StepUpAction =
  | { type: "restore"; revision: number; reason: string }
  | { type: "transfer"; reportId: string; ownerId: string; preparerId: string | null; reason: string };

export function AdminIncidentWorkspace() {
  const { incidentId = "" } = useParams();
  const [detail, setDetail] = useState<AdminIncidentDetail | null>(null);
  const [staff, setStaff] = useState<AdminStaffMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recordsStatus, setRecordsStatus] = useState<"in_progress" | "completed" | "archived">("in_progress");
  const [statusBusy, setStatusBusy] = useState(false);
  const [restoreRevision, setRestoreRevision] = useState("");
  const [restoreReason, setRestoreReason] = useState("");
  const [transferReportId, setTransferReportId] = useState("");
  const [transferOwnerId, setTransferOwnerId] = useState("");
  const [transferPreparerId, setTransferPreparerId] = useState("");
  const [transferReason, setTransferReason] = useState("");
  const [pending, setPending] = useState<StepUpAction | null>(null);
  const [stepUpBusy, setStepUpBusy] = useState(false);
  const [stepUpError, setStepUpError] = useState<string | null>(null);

  async function reload() {
    if (!incidentId) return;
    setLoading(true);
    setError(null);
    try {
      const [incident, staffPage] = await Promise.all([
        getAdminIncidentDetail(incidentId),
        listAdminStaff(),
      ]);
      setDetail(incident);
      setStaff(staffPage.items);
      setRecordsStatus(incident.recordsStatus as "in_progress" | "completed" | "archived");
      setTransferReportId((current) => current || incident.reports[0]?.reportId || "");
      setTransferOwnerId((current) => current || incident.reports[0]?.reportingOfficer.staffId || "");
      setTransferPreparerId((current) => current || incident.reports[0]?.preparer.staffId || "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Administrator incident controls could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
    // The route identifier is the complete load key.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [incidentId]);

  const selectedReport = useMemo(
    () => detail?.reports.find((report) => report.reportId === transferReportId) ?? null,
    [detail, transferReportId],
  );

  async function saveRecordsStatus() {
    if (!detail || recordsStatus === detail.recordsStatus) return;
    setStatusBusy(true);
    setError(null);
    try {
      const updated = await changeAdminRecordsStatus(
        detail.incidentId,
        recordsStatus,
        detail.currentRevisionNumber,
      );
      setDetail(updated);
      setRecordsStatus(updated.recordsStatus as "in_progress" | "completed" | "archived");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Records status could not be changed.");
    } finally {
      setStatusBusy(false);
    }
  }

  function requestRestore() {
    const revision = Number(restoreRevision);
    if (!Number.isInteger(revision) || revision < 1 || !restoreReason.trim()) {
      setError("Enter a valid historical revision and a reason before restoring.");
      return;
    }
    setPending({ type: "restore", revision, reason: restoreReason.trim() });
    setStepUpError(null);
  }

  function requestTransfer() {
    if (!transferReportId || !transferOwnerId || !transferReason.trim()) {
      setError("Choose a report, new reporting officer, and reason before transferring ownership.");
      return;
    }
    setPending({
      type: "transfer",
      reportId: transferReportId,
      ownerId: transferOwnerId,
      preparerId: transferPreparerId || null,
      reason: transferReason.trim(),
    });
    setStepUpError(null);
  }

  async function confirmStepUp(pin: string) {
    if (!pending || !detail) return;
    setStepUpBusy(true);
    setStepUpError(null);
    try {
      if (pending.type === "restore") {
        const updated = await restoreAdminIncident(
          detail.incidentId,
          pending.revision,
          pending.reason,
          pin,
        );
        setDetail(updated);
        setRecordsStatus(updated.recordsStatus as "in_progress" | "completed" | "archived");
        setRestoreRevision("");
        setRestoreReason("");
      } else {
        await transferAdminReport(
          pending.reportId,
          pending.ownerId,
          pending.preparerId,
          pending.reason,
          pin,
        );
        setTransferReason("");
        await reload();
      }
      setPending(null);
    } catch (reason) {
      setStepUpError(reason instanceof Error ? reason.message : "The administrator action could not be completed.");
    } finally {
      setStepUpBusy(false);
    }
  }

  return (
    <div className="admin-incident-workspace">
      <div className="admin-incident-toolbar">
        <Link to="/admin/incidents" className="admin-back-link">← All Incidents</Link>
        <span>Administrator review context</span>
      </div>
      <AdminAttributionBanner />

      <section className="admin-incident-control-rail" aria-label="Administrator incident controls">
        {loading ? <div className="admin-loading-panel" aria-busy="true">Loading administrator incident controls…</div> : null}
        {error ? <div className="admin-alert error" role="alert">{error}</div> : null}
        {detail ? (
          <>
            <div className="admin-incident-control-head">
              <div>
                <p>Administrative record controls</p>
                <h2>{detail.incidentNumber ?? "Unnumbered Incident"}</h2>
                <span>{detail.incidentName ?? "Incident name not entered"}</span>
              </div>
              <div className="admin-control-revision">Revision {detail.currentRevisionNumber}</div>
            </div>

            <div className="admin-control-grid">
              <section className="admin-control-card">
                <div className="admin-control-card-heading"><span aria-hidden="true">◆</span><div><strong>Records status</strong><small>Separate from officer workflow progress</small></div></div>
                <label>Records status
                  <select value={recordsStatus} onChange={(event) => setRecordsStatus(event.target.value as typeof recordsStatus)}>
                    <option value="in_progress">In progress</option>
                    <option value="completed">Completed</option>
                    <option value="archived">Archived</option>
                  </select>
                </label>
                <button className="admin-secondary-button" type="button" disabled={statusBusy || recordsStatus === detail.recordsStatus} onClick={() => void saveRecordsStatus()}>
                  {statusBusy ? "Saving…" : "Save records status"}
                </button>
              </section>

              <section className="admin-control-card">
                <div className="admin-control-card-heading"><span aria-hidden="true">↶</span><div><strong>Restore revision</strong><small>Creates a new attributed revision</small></div></div>
                <div className="admin-control-inline-fields">
                  <label>Restore revision<input aria-label="Restore revision" inputMode="numeric" value={restoreRevision} onChange={(event) => setRestoreRevision(event.target.value)} placeholder="Revision #" /></label>
                  <label>Restore reason<input aria-label="Restore reason" value={restoreReason} onChange={(event) => setRestoreReason(event.target.value)} placeholder="Required reason" /></label>
                </div>
                <button className="admin-secondary-button" type="button" onClick={requestRestore}>Restore revision</button>
              </section>

              <section className="admin-control-card admin-transfer-card">
                <div className="admin-control-card-heading"><span aria-hidden="true">⇄</span><div><strong>Transfer report ownership</strong><small>Changes are attributed and audited</small></div></div>
                <div className="admin-transfer-fields">
                  <label>Report<select value={transferReportId} onChange={(event) => {
                    const reportId = event.target.value;
                    setTransferReportId(reportId);
                    const report = detail.reports.find((item) => item.reportId === reportId);
                    setTransferOwnerId(report?.reportingOfficer.staffId ?? "");
                    setTransferPreparerId(report?.preparer.staffId ?? "");
                  }}>
                    {detail.reports.map((report) => <option key={report.reportId} value={report.reportId}>{report.reportType.replaceAll("_", " ")} · {report.reportingOfficer.displayName}</option>)}
                  </select></label>
                  <label>New reporting officer<select value={transferOwnerId} onChange={(event) => setTransferOwnerId(event.target.value)}>{staff.map((person) => <option key={person.staffId} value={person.staffId}>{person.displayName} · {person.employeeNumber}</option>)}</select></label>
                  <label>Preparer<select value={transferPreparerId} onChange={(event) => setTransferPreparerId(event.target.value)}><option value="">Same as reporting officer / none</option>{staff.map((person) => <option key={person.staffId} value={person.staffId}>{person.displayName}</option>)}</select></label>
                  <label>Reason<input value={transferReason} onChange={(event) => setTransferReason(event.target.value)} placeholder="Required reason" /></label>
                </div>
                <div className="admin-transfer-summary">Current owner: <strong>{selectedReport?.reportingOfficer.displayName ?? "No report selected"}</strong></div>
                <button className="admin-secondary-button" type="button" disabled={!detail.reports.length} onClick={requestTransfer}>Transfer ownership</button>
              </section>
            </div>
          </>
        ) : null}
      </section>

      <DocumentStudioPage />

      {pending ? (
        <AdminStepUpDialog
          title={pending.type === "restore" ? "Confirm incident restore" : "Confirm report transfer"}
          description={pending.type === "restore"
            ? `Restore historical revision ${pending.revision}. The restored state becomes a new revision and remains attributed to your administrator account.`
            : "Confirm the report ownership change. The transfer is logged under your administrator account."}
          confirmLabel={pending.type === "restore" ? "Restore revision" : "Transfer ownership"}
          busy={stepUpBusy}
          error={stepUpError}
          onCancel={() => { setPending(null); setStepUpError(null); }}
          onConfirm={confirmStepUp}
        />
      ) : null}
    </div>
  );
}
