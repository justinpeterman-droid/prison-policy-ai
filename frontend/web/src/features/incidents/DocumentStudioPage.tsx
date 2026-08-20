import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { InterfaceIcon } from "../../components/InterfaceIcon";
import { WebApiError } from "../../api/client";
import {
  acknowledgePhysical,
  downloadReportDocx,
  getFormPreview,
  getIncident,
  getPacket,
  getPhysicalGuidance,
  getReport,
  listIncidentRevisions,
  listReportRevisions,
  listReports,
  populatePacketItem,
  recordDocumentAction,
  saveReport,
  type FormPreview,
  type IncidentRecord,
  type IncidentRevision,
  type PacketItem,
  type PhysicalGuidance,
  type ReportDetail,
  type ReportRevision,
  type ReportSummary,
} from "./api";

const TABS = [
  "Overview",
  "Officer Reports",
  "Copy to Records",
  "Required Paperwork",
  "Notes & Facts",
  "History",
] as const;

type Tab = (typeof TABS)[number];

function titleCase(value: string): string {
  return value
    .split("_")
    .map((part) => part ? `${part[0].toUpperCase()}${part.slice(1)}` : part)
    .join(" ");
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not entered";
  if (Array.isArray(value)) return value.map(display).join(", ");
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

function statusTone(state: string): string {
  if (state === "ready") return "ready";
  if (state === "missing_information") return "warning";
  return "review";
}

function CopyReportCard({
  report,
  onSaved,
}: {
  report: ReportDetail;
  onSaved: (next: ReportDetail) => void;
}) {
  const [text, setText] = useState(report.content.narrative);
  const [state, setState] = useState<"idle" | "saving" | "copied" | "error">("idle");
  const label = titleCase(report.report_type);

  useEffect(() => setText(report.content.narrative), [report]);

  async function save() {
    setState("saving");
    try {
      const next = await saveReport(report, text);
      onSaved(next);
      setState("idle");
    } catch {
      setState("error");
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      await recordDocumentAction({
        incident_id: report.incident_id,
        incident_revision_number: report.source_incident_revision_number ?? 1,
        report_id: report.report_id,
        action: "copy_text",
      });
      setState("copied");
      window.setTimeout(() => setState("idle"), 1800);
    } catch {
      setState("error");
    }
  }

  return (
    <article className="iw-copy-card">
      <div className="iw-document-card-heading">
        <div>
          <span className="iw-document-kicker">Copy to Records</span>
          <h3>{label}</h3>
        </div>
        <span className="iw-copy-only-badge">Copy only</span>
      </div>
      <textarea
        aria-label={`${label} text`}
        value={text}
        onChange={(event) => setText(event.target.value)}
        rows={12}
      />
      <div className="iw-document-actions">
        <button className="iw-button iw-button-secondary" type="button" onClick={() => void save()}>
          {state === "saving" ? "Saving…" : "Save Text"}
        </button>
        <button
          className="iw-button iw-button-gold"
          type="button"
          aria-label={`Copy ${label}`}
          onClick={() => void copy()}
        >
          {state === "copied" ? "Copied" : "Copy"}
        </button>
      </div>
      {state === "error" ? <p className="iw-inline-error" role="alert">The text could not be saved or copied. It remains visible.</p> : null}
    </article>
  );
}

function DigitalFormCard({
  item,
  incident,
  onPreview,
  onRefresh,
}: {
  item: PacketItem;
  incident: IncidentRecord;
  onPreview: (preview: FormPreview) => void;
  onRefresh: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const completeness = item.form_instance?.completeness;

  async function preview() {
    setBusy(true);
    try {
      let instance = item.form_instance;
      if (!instance) {
        instance = await populatePacketItem(
          item.packet_item_id,
          incident.current_revision_number,
        );
        await onRefresh();
      }
      onPreview(await getFormPreview(instance.form_instance_id));
    } finally {
      setBusy(false);
    }
  }

  async function print() {
    setBusy(true);
    try {
      let instance = item.form_instance;
      if (!instance) {
        instance = await populatePacketItem(
          item.packet_item_id,
          incident.current_revision_number,
        );
        await onRefresh();
      }
      const form = await getFormPreview(instance.form_instance_id);
      onPreview(form);
      await recordDocumentAction({
        incident_id: incident.incident_id,
        incident_revision_number: incident.current_revision_number,
        packet_item_id: item.packet_item_id,
        action: "print",
      });
      window.setTimeout(() => window.print(), 50);
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="iw-paperwork-card">
      <div className="iw-document-card-heading">
        <div>
          <span className="iw-document-kicker">{titleCase(item.packet_group)}</span>
          <h3>{item.name}</h3>
        </div>
        <span className={`iw-completeness iw-completeness-${statusTone(completeness?.state ?? "needs_review")}`}>
          {completeness ? titleCase(completeness.state) : "Not populated"}
        </span>
      </div>
      <p>{item.selection_reason}</p>
      {completeness?.missing_fields.length ? (
        <p className="iw-field-warning">
          Missing: {completeness.missing_fields.map(titleCase).join(", ")}
        </p>
      ) : null}
      <div className="iw-document-actions">
        {item.allowed_actions.includes("preview") ? (
          <button
            className="iw-button iw-button-secondary"
            type="button"
            aria-label={`Preview ${item.name}`}
            disabled={busy}
            onClick={() => void preview()}
          >
            {busy ? "Opening…" : "Preview"}
          </button>
        ) : null}
        {item.allowed_actions.includes("print") ? (
          <button
            className="iw-button iw-button-primary"
            type="button"
            aria-label={`Print ${item.name}`}
            disabled={busy}
            onClick={() => void print()}
          >
            Print
          </button>
        ) : null}
      </div>
    </article>
  );
}

function PhysicalCard({ item, onOpen }: { item: PacketItem; onOpen: () => void }) {
  return (
    <article className="iw-paperwork-card iw-physical-card">
      <div className="iw-document-card-heading">
        <div>
          <span className="iw-document-kicker">Physical paperwork</span>
          <h3>{item.name}</h3>
        </div>
        <span className="iw-physical-badge">Handwritten</span>
      </div>
      <p>{item.selection_reason}</p>
      <p className="iw-field-warning">A generated digital substitute is not permitted.</p>
      <div className="iw-document-actions">
        <button
          className="iw-button iw-button-secondary"
          type="button"
          aria-label="Open physical Chain of Custody guidance"
          onClick={onOpen}
        >
          Open Guidance
        </button>
      </div>
    </article>
  );
}

export function DocumentStudioPage() {
  const { incidentId } = useParams<{ incidentId: string }>();
  const [incident, setIncident] = useState<IncidentRecord | null>(null);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [packet, setPacket] = useState<PacketItem[]>([]);
  const [copyDetails, setCopyDetails] = useState<Record<string, ReportDetail>>({});
  const [selectedReport, setSelectedReport] = useState<ReportDetail | null>(null);
  const [reportText, setReportText] = useState("");
  const [preview, setPreview] = useState<FormPreview | null>(null);
  const [physical, setPhysical] = useState<PhysicalGuidance | null>(null);
  const [history, setHistory] = useState<{
    incident: IncidentRevision[];
    reports: ReportRevision[];
  }>({ incident: [], reports: [] });
  const [tab, setTab] = useState<Tab>("Overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function refreshPacket() {
    if (!incidentId) return;
    setPacket(await getPacket(incidentId));
  }

  useEffect(() => {
    if (!incidentId) return;
    let active = true;
    setLoading(true);
    void Promise.all([
      getIncident(incidentId),
      listReports(incidentId),
      getPacket(incidentId),
    ]).then(
      ([incidentData, reportData, packetData]) => {
        if (!active) return;
        setIncident(incidentData);
        setReports(reportData);
        setPacket(packetData);
        setLoading(false);
      },
      (reason: unknown) => {
        if (!active) return;
        setError(reason instanceof WebApiError ? reason.message : "The incident could not be loaded.");
        setLoading(false);
      },
    );
    return () => { active = false; };
  }, [incidentId]);

  useEffect(() => {
    if (tab !== "Copy to Records") return;
    const copyReports = reports.filter((report) => report.presentation === "copy_text");
    const missing = copyReports.filter((report) => !copyDetails[report.report_id]);
    if (!missing.length) return;
    let active = true;
    void Promise.all(missing.map((report) => getReport(report.report_id))).then((items) => {
      if (!active) return;
      setCopyDetails((current) => ({
        ...current,
        ...Object.fromEntries(items.map((item) => [item.report_id, item])),
      }));
    }).catch((reason: unknown) => {
      if (active) setNotice(reason instanceof Error ? reason.message : "Copy-only text could not be loaded.");
    });
    return () => { active = false; };
  }, [tab, reports, copyDetails]);

  useEffect(() => {
    if (tab !== "History" || !incidentId) return;
    let active = true;
    void Promise.all([
      listIncidentRevisions(incidentId),
      Promise.all(reports.map((report) => listReportRevisions(report.report_id))),
    ]).then(([incidentRows, reportRows]) => {
      if (!active) return;
      setHistory({ incident: incidentRows, reports: reportRows.flat() });
    }).catch(() => {
      if (active) setNotice("Revision history could not be loaded.");
    });
    return () => { active = false; };
  }, [tab, incidentId, reports]);

  const documentReports = useMemo(
    () => reports.filter((report) => report.presentation === "document"),
    [reports],
  );
  const copyReports = useMemo(
    () => reports.filter((report) => report.presentation === "copy_text"),
    [reports],
  );
  const selectedPacket = useMemo(
    () => packet.filter((item) => item.packet_state === "selected"),
    [packet],
  );

  async function openReport(report: ReportSummary) {
    try {
      const detail = await getReport(report.report_id);
      setSelectedReport(detail);
      setReportText(detail.content.narrative);
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : "The report could not be opened.");
    }
  }

  async function saveSelectedReport() {
    if (!selectedReport) return;
    try {
      const saved = await saveReport(selectedReport, reportText);
      setSelectedReport(saved);
      setReportText(saved.content.narrative);
      setNotice("Report saved.");
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : "The report could not be saved. Text remains visible.");
    }
  }

  async function printReport(report: ReportSummary) {
    if (!incident) return;
    await recordDocumentAction({
      incident_id: incident.incident_id,
      incident_revision_number: incident.current_revision_number,
      report_id: report.report_id,
      action: "print",
    });
    window.print();
  }

  async function openPhysical(item: PacketItem) {
    try {
      setPhysical(await getPhysicalGuidance(item.packet_item_id));
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : "Physical guidance could not be opened.");
    }
  }

  async function markPhysicalComplete() {
    if (!physical) return;
    try {
      const acknowledgment = await acknowledgePhysical(
        physical.packet_item_id,
        "Official physical carbon-copy form completed by hand.",
      );
      setPhysical({ ...physical, acknowledgment });
      await refreshPacket();
      setNotice("Physical form completion recorded.");
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : "Completion could not be recorded.");
    }
  }

  if (loading) {
    return <section className="iw-page"><div className="iw-loading-panel" aria-busy="true">Opening Document Studio…</div></section>;
  }
  if (error || !incident) {
    return <section className="iw-page"><div className="iw-callout iw-callout-error" role="alert"><strong>Incident unavailable</strong><p>{error ?? "The incident could not be found."}</p><Link className="iw-button iw-button-secondary" to="/reports">Back to Reports</Link></div></section>;
  }

  return (
    <section className="iw-page iw-studio" aria-labelledby="studio-heading">
      <header className="iw-studio-header">
        <div>
          <Link className="iw-back-link" to="/reports"><InterfaceIcon name="arrow-left" /> Reports</Link>
          <p className="iw-number">{incident.incident_number || "Unnumbered Incident"}</p>
          <h1 id="studio-heading">{incident.incident_name || "Incident name not assigned"}</h1>
          <p>{incident.location || "Location not entered"} · {incident.category ? titleCase(incident.category) : "Not classified"} · Revision {incident.current_revision_number}</p>
        </div>
        <div className="iw-studio-progress">
          <span>Document Studio</span>
          <strong>{documentReports.length + copyReports.length} reports · {selectedPacket.length} paperwork items</strong>
        </div>
      </header>

      {notice ? <div className="iw-notice" role="status"><span>{notice}</span><button type="button" aria-label="Dismiss notice" onClick={() => setNotice(null)}><InterfaceIcon name="close" /></button></div> : null}

      <div className="iw-tabs" role="tablist" aria-label="Incident document areas">
        {TABS.map((label) => (
          <button
            key={label}
            type="button"
            role="tab"
            aria-selected={tab === label}
            className={tab === label ? "active" : ""}
            onClick={() => setTab(label)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="iw-studio-content">
        {tab === "Overview" ? (
          <div className="iw-overview-grid">
            <article className="iw-overview-card"><span>Reporting officers</span><strong>{incident.reporting_officers.length}</strong><p>{incident.reporting_officers.map((officer) => officer.display_name).join(", ") || "None selected"}</p></article>
            <article className="iw-overview-card"><span>Officer reports</span><strong>{documentReports.length}</strong><p>Editable, revisioned, and printable when permitted.</p></article>
            <article className="iw-overview-card"><span>Copy to Records</span><strong>{copyReports.length}</strong><p>Clean text for the external records database.</p></article>
            <article className="iw-overview-card"><span>Required paperwork</span><strong>{selectedPacket.filter((item) => item.packet_group === "required").length}</strong><p>Automatically organized from the incident checklist.</p></article>
            <article className="iw-overview-card iw-overview-card-wide"><span>Current incident facts</span><dl className="iw-overview-facts"><div><dt>Date and time</dt><dd>{incident.incident_date || "Not entered"} {incident.incident_time || ""}</dd></div><div><dt>Location</dt><dd>{incident.location || "Not entered"}</dd></div><div><dt>Category</dt><dd>{incident.category ? titleCase(incident.category) : "Not classified"}</dd></div><div><dt>Facility and shift</dt><dd>{incident.facility || "Not entered"} {incident.shift ? `· ${incident.shift} Shift` : ""}</dd></div></dl></article>
          </div>
        ) : null}

        {tab === "Officer Reports" ? (
          <div className="iw-document-layout">
            <aside className="iw-document-list" aria-label="Officer reports">
              {documentReports.map((report) => <button type="button" key={report.report_id} className={selectedReport?.report_id === report.report_id ? "active" : ""} onClick={() => void openReport(report)}><span>{titleCase(report.report_type)}</span><small>{report.reporting_officer.display_name}</small></button>)}
              {!documentReports.length ? <p>No officer reports have been generated.</p> : null}
            </aside>
            <div className="iw-editor-panel">
              {selectedReport ? <><div className="iw-editor-header"><div><span>{titleCase(selectedReport.report_type)}</span><strong>{selectedReport.reporting_officer.display_name}</strong></div><span>Revision {selectedReport.current_revision_number}</span></div><textarea aria-label={`${titleCase(selectedReport.report_type)} narrative`} rows={22} value={reportText} onChange={(event) => setReportText(event.target.value)} /><div className="iw-document-actions"><button className="iw-button iw-button-secondary" type="button" onClick={() => void saveSelectedReport()}>Save Report</button>{selectedReport.allowed_actions.includes("print") ? <button className="iw-button iw-button-primary" type="button" onClick={() => void printReport(selectedReport)}>Print</button> : null}{selectedReport.allowed_actions.includes("download_word") ? <button className="iw-button iw-button-gold" type="button" onClick={() => void downloadReportDocx(selectedReport)}>Download Word</button> : null}</div></> : <div className="iw-empty-inline"><strong>Select an officer report</strong><p>The report will open here without leaving the incident.</p></div>}
            </div>
          </div>
        ) : null}

        {tab === "Copy to Records" ? (
          <div className="iw-copy-grid">
            {copyReports.map((summary) => {
              const detail = copyDetails[summary.report_id];
              return detail ? <CopyReportCard key={detail.report_id} report={detail} onSaved={(next) => setCopyDetails((current) => ({ ...current, [next.report_id]: next }))} /> : <article className="iw-copy-card" key={summary.report_id} aria-busy="true">Loading {titleCase(summary.report_type)}…</article>;
            })}
            {!copyReports.length ? <div className="iw-empty-state"><h2>No copy-only outputs are required</h2><p>Supervisor summaries and disciplinary supplements will appear here when generated.</p></div> : null}
          </div>
        ) : null}

        {tab === "Required Paperwork" ? (
          <div className="iw-paperwork-layout">
            <div className="iw-paperwork-groups">
              {(["required", "recommended", "additional"] as const).map((group) => {
                const items = selectedPacket.filter((item) => item.packet_group === group);
                return <section key={group} className="iw-paperwork-group"><div className="iw-group-heading"><div><span>{titleCase(group)}</span><h2>{group === "required" ? "Required Paperwork" : `${titleCase(group)} Forms`}</h2></div><strong>{items.length}</strong></div><div className="iw-paperwork-grid">{items.map((item) => item.presentation === "physical" ? <PhysicalCard key={item.packet_item_id} item={item} onOpen={() => void openPhysical(item)} /> : <DigitalFormCard key={item.packet_item_id} item={item} incident={incident} onPreview={setPreview} onRefresh={refreshPacket} />)}{!items.length ? <p className="iw-muted-line">No {group} items are selected.</p> : null}</div></section>;
              })}
            </div>
            <aside className="iw-inspector" aria-label="Paperwork inspector">
              {physical ? <div className="iw-physical-guidance"><span className="iw-physical-warning">{physical.warning}</span><h2>{physical.name}</h2><p>{physical.description}</p><dl><div><dt>Obtain from</dt><dd>{physical.obtain_from}</dd></div>{physical.guidance_fields.map((field) => <div key={field}><dt>{titleCase(field)}</dt><dd>{display(physical.guidance_values[field])}</dd></div>)}</dl>{physical.acknowledgment ? <div className="iw-complete-callout"><strong>Physical form completion recorded</strong><p>{physical.acknowledgment.note}</p></div> : <button className="iw-button iw-button-gold" type="button" onClick={() => void markPhysicalComplete()}>Mark Physical Form Completed</button>}<button className="iw-text-button" type="button" onClick={() => setPhysical(null)}>Close guidance</button></div> : preview ? <div className="iw-form-preview"><div className="iw-preview-toolbar"><div><span>Document preview</span><h2>{preview.template_name}</h2></div><button type="button" aria-label="Close form preview" onClick={() => setPreview(null)}><InterfaceIcon name="close" /></button></div><div className="iw-paper-sheet">{Object.entries(preview.fields).map(([key, value]) => <div className="iw-preview-field" key={key}><span>{titleCase(key)}</span><strong>{display(value)}</strong></div>)}</div><div className={`iw-completeness-panel iw-completeness-${statusTone(preview.completeness.state)}`}><strong>{titleCase(preview.completeness.state)}</strong>{preview.completeness.missing_fields.length ? <p>Missing: {preview.completeness.missing_fields.map(titleCase).join(", ")}</p> : <p>Required information is present.</p>}</div></div> : <div className="iw-inspector-empty"><span><InterfaceIcon name="paperwork" /></span><h2>Paperwork inspector</h2><p>Preview a populated form or open physical-form guidance here.</p></div>}
            </aside>
          </div>
        ) : null}

        {tab === "Notes & Facts" ? (
          <div className="iw-facts-layout"><article className="iw-facts-panel"><span>Officer field notes</span><h2>Saved notes</h2><pre>{incident.field_notes || "No field notes entered."}</pre></article><article className="iw-facts-panel"><span>Reviewed information</span><h2>Extracted facts</h2><dl>{Object.entries(incident.extracted_facts).map(([key, value]) => <div key={key}><dt>{titleCase(key)}</dt><dd>{display(value)}</dd></div>)}</dl>{!Object.keys(incident.extracted_facts).length ? <p>No extracted facts are saved.</p> : null}</article><article className="iw-facts-panel"><span>Missing information</span><h2>Officer answers</h2><dl>{Object.entries(incident.gap_answers).map(([key, value]) => <div key={key}><dt>{titleCase(key)}</dt><dd>{display(value)}</dd></div>)}</dl>{!Object.keys(incident.gap_answers).length ? <p>No missing-information answers are saved.</p> : null}</article></div>
        ) : null}

        {tab === "History" ? (
          <div className="iw-history-layout"><section><h2>Incident revisions</h2><ol className="iw-history-list">{history.incident.map((row) => <li key={row.revision_id}><span>Revision {row.revision_number}</span><strong>{titleCase(row.reason)}</strong><small>{new Date(row.created_at).toLocaleString()}</small></li>)}</ol></section><section><h2>Report revisions</h2><ol className="iw-history-list">{history.reports.map((row) => <li key={row.revision_id}><span>Revision {row.revision_number}</span><strong>{row.editor_display_name}</strong><small>{new Date(row.created_at).toLocaleString()}</small></li>)}</ol></section></div>
        ) : null}
      </div>
    </section>
  );
}
