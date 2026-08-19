import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { WebApiError } from "../../api/client";
import type { SessionProfile } from "../auth/api";
import {
  createIncident,
  getJob,
  listReports,
  rebuildPacket,
  saveIncident,
  submitJob,
  type IncidentRecord,
  type PacketItem,
  type ReportSummary,
} from "./api";

const STEPS = [
  "Officers",
  "Field Notes",
  "Review Facts",
  "Missing Information",
  "Reports",
  "Forms & Export",
] as const;

type SaveState = "saved" | "saving" | "unsaved" | "reconnecting" | "failed";

function saveStateLabel(value: SaveState): string {
  return {
    saved: "All changes saved",
    saving: "Saving…",
    unsaved: "Unsaved changes",
    reconnecting: "Reconnecting — work preserved",
    failed: "Save failed — work preserved",
  }[value];
}

function normalizeNumber(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length === 9) {
    return `${digits.slice(0, 4)}-${digits.slice(4, 6)}-${digits.slice(6)}`;
  }
  return value.trim();
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not yet known";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

interface NewReportPageProps {
  profile: SessionProfile;
}

export function NewReportPage({ profile }: NewReportPageProps) {
  const [step, setStep] = useState(0);
  const [incident, setIncident] = useState<IncidentRecord | null>(null);
  const [incidentNumber, setIncidentNumber] = useState("");
  const [incidentName, setIncidentName] = useState("");
  const [incidentDate, setIncidentDate] = useState("");
  const [incidentTime, setIncidentTime] = useState("");
  const [facility, setFacility] = useState("");
  const [location, setLocation] = useState("");
  const [category, setCategory] = useState("");
  const [fieldNotes, setFieldNotes] = useState("");
  const [facts, setFacts] = useState<Record<string, unknown>>({});
  const [gapAnswers, setGapAnswers] = useState<Record<string, string>>({
    medical_disposition: "",
    photo_video_obtained: "",
    drug_test_disposition: "",
  });
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [packet, setPacket] = useState<PacketItem[]>([]);
  const [jobMessage, setJobMessage] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("unsaved");
  const [message, setMessage] = useState<string | null>(null);

  const officialNumber = incident?.incident_number ?? normalizeNumber(incidentNumber);
  const currentStepLabel = STEPS[step];

  useEffect(() => {
    if (!incident || step !== 4) return;
    let active = true;
    void listReports(incident.incident_id).then((items) => {
      if (active) setReports(items);
    }).catch(() => {
      if (active) setJobMessage("Reports are temporarily unavailable. Your incident is still saved.");
    });
    return () => { active = false; };
  }, [incident, step]);

  const missingCount = useMemo(
    () => Object.values(gapAnswers).filter((value) => !value.trim()).length,
    [gapAnswers],
  );

  function markUnsaved() {
    setSaveState("unsaved");
    setMessage(null);
  }

  async function saveNotesAndContinue() {
    setSaveState("saving");
    setMessage(null);
    try {
      const saved = incident
        ? await saveIncident(incident, {
            incident_number: normalizeNumber(incidentNumber) || null,
            incident_name: incidentName.trim() || null,
            incident_date: incidentDate || null,
            incident_time: incidentTime || null,
            facility: facility.trim() || null,
            shift: profile.shift,
            location: location.trim() || null,
            category: category.trim() || null,
            field_notes: fieldNotes,
          })
        : await createIncident({
            reporting_staff_ids: [profile.staffId],
            incident_number: normalizeNumber(incidentNumber) || null,
            incident_name: incidentName.trim() || null,
            incident_date: incidentDate || null,
            incident_time: incidentTime || null,
            facility: facility.trim() || null,
            shift: profile.shift,
            location: location.trim() || null,
            category: category.trim() || null,
            field_notes: fieldNotes,
            classification: {},
            extracted_facts: {},
            gap_answers: {},
            charges: [],
            validation: {},
            warnings: [],
          });
      setIncident(saved);
      setIncidentNumber(saved.incident_number ?? incidentNumber);
      setIncidentName(saved.incident_name ?? incidentName);
      setFacts(saved.extracted_facts);
      setGapAnswers((current) => ({
        ...current,
        ...Object.fromEntries(
          Object.entries(saved.gap_answers).map(([key, value]) => [key, String(value ?? "")]),
        ),
      }));
      setSaveState("saved");
      setStep(2);
    } catch (reason) {
      const error = reason instanceof WebApiError ? reason : null;
      setMessage(error?.message ?? "The incident could not be saved. Your visible work has not been cleared.");
      setSaveState(error?.code === "network_unavailable" ? "reconnecting" : "failed");
    }
  }

  async function confirmFacts() {
    if (!incident) return;
    setSaveState("saving");
    try {
      const saved = await saveIncident(incident, {
        category: category.trim() || incident.category,
        location: location.trim() || incident.location,
        extracted_facts: facts,
        validation: { ...incident.validation, facts_reviewed: true },
      });
      setIncident(saved);
      setSaveState("saved");
      setStep(3);
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Facts could not be saved.");
      setSaveState("failed");
    }
  }

  async function saveMissingInformation() {
    if (!incident) return;
    setSaveState("saving");
    try {
      const saved = await saveIncident(incident, {
        gap_answers: gapAnswers,
        validation: {
          ...incident.validation,
          facts_reviewed: true,
          missing_information_reviewed: true,
        },
      });
      setIncident(saved);
      setSaveState("saved");
      setStep(4);
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Missing information could not be saved.");
      setSaveState("failed");
    }
  }

  async function startJob(jobType: "classify" | "extract" | "generate") {
    if (!incident) return;
    setJobMessage(`${jobType === "generate" ? "Generating reports" : "Reviewing incident information"}…`);
    try {
      let job = await submitJob(incident.incident_id, jobType, incident.current_revision_number);
      for (let attempt = 0; attempt < 12 && ["queued", "running"].includes(job.state); attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 500));
        job = await getJob(job.job_id);
      }
      if (job.state === "succeeded") {
        setJobMessage(jobType === "generate" ? "Reports are ready for review." : "Incident information is ready to review.");
        if (jobType === "generate") setReports(await listReports(incident.incident_id));
      } else if (job.state === "failed") {
        setJobMessage("The request did not complete. Your saved incident is unchanged.");
      } else {
        setJobMessage("The request is still running. You may safely reopen this incident later.");
      }
    } catch (reason) {
      setJobMessage(reason instanceof Error ? reason.message : "The request could not be started.");
    }
  }

  async function preparePaperwork() {
    if (!incident) return;
    setSaveState("saving");
    try {
      const items = await rebuildPacket(incident.incident_id, incident.current_revision_number);
      setPacket(items);
      setSaveState("saved");
      setStep(5);
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Paperwork could not be prepared.");
      setSaveState("failed");
    }
  }

  return (
    <section className="iw-page iw-new-report" aria-labelledby="new-report-heading">
      <header className="iw-page-header iw-page-header-compact">
        <div>
          <p className="iw-eyebrow">Guided Operations Workspace</p>
          <h1 id="new-report-heading">New Report</h1>
          <p>Complete one guided incident package without hunting through disconnected forms.</p>
        </div>
        <div className={`iw-save-state iw-save-${saveState}`} role="status" aria-live="polite">
          <span aria-hidden="true" />
          {saveStateLabel(saveState)}
        </div>
      </header>

      <ol className="iw-stepper" aria-label="Report workflow">
        {STEPS.map((label, index) => (
          <li key={label} className={index === step ? "active" : index < step ? "complete" : ""}>
            <span className="iw-step-number">{index < step ? "✓" : index + 1}</span>
            <span>{label}</span>
          </li>
        ))}
      </ol>

      {message ? <div className="iw-callout iw-callout-error" role="alert"><strong>Work preserved</strong><p>{message}</p></div> : null}

      <div className="iw-wizard-card">
        <div className="iw-wizard-heading">
          <div>
            <p className="iw-eyebrow">Step {step + 1} of {STEPS.length}</p>
            <h2>{currentStepLabel}</h2>
          </div>
          {officialNumber ? <span className="iw-number-chip">{officialNumber}</span> : null}
        </div>

        {step === 0 ? (
          <div className="iw-wizard-content">
            <div className="iw-officer-selection">
              <span className="iw-avatar-large" aria-hidden="true">
                {profile.displayName.split(/\s+/).slice(-2).map((part) => part[0]).join("")}
              </span>
              <div><strong>{profile.displayName}</strong><p>Current reporting officer · {profile.shift ? `${profile.shift} Shift` : "Shift not assigned"}</p></div>
              <span className="iw-selected-badge">Selected</span>
            </div>
            <div className="iw-form-grid iw-form-grid-three">
              <label className="iw-field"><span>Incident number</span><input value={incidentNumber} onChange={(event) => { setIncidentNumber(event.target.value); markUnsaved(); }} placeholder="2026-08-029" /></label>
              <label className="iw-field"><span>Incident name</span><input value={incidentName} onChange={(event) => { setIncidentName(event.target.value); markUnsaved(); }} placeholder="Barracks 4 Fight" /></label>
              <label className="iw-field"><span>Facility</span><input value={facility} onChange={(event) => { setFacility(event.target.value); markUnsaved(); }} placeholder="Facility or unit" /></label>
              <label className="iw-field"><span>Date</span><input type="date" value={incidentDate} onChange={(event) => { setIncidentDate(event.target.value); markUnsaved(); }} /></label>
              <label className="iw-field"><span>Time</span><input type="time" value={incidentTime} onChange={(event) => { setIncidentTime(event.target.value); markUnsaved(); }} /></label>
              <label className="iw-field"><span>Location</span><input value={location} onChange={(event) => { setLocation(event.target.value); markUnsaved(); }} placeholder="Barracks, cell, hall, or area" /></label>
              <label className="iw-field iw-field-wide"><span>Initial category, when known</span><input value={category} onChange={(event) => { setCategory(event.target.value); markUnsaved(); }} placeholder="Fight, contraband, assault, use of force…" /></label>
            </div>
            <div className="iw-wizard-actions"><span /><button className="iw-button iw-button-gold" type="button" onClick={() => setStep(1)}>Continue to Field Notes</button></div>
          </div>
        ) : null}

        {step === 1 ? (
          <div className="iw-wizard-content">
            <label className="iw-field iw-notes-field">
              <span>Officer field notes</span>
              <textarea value={fieldNotes} onChange={(event) => { setFieldNotes(event.target.value); markUnsaved(); }} rows={15} maxLength={50000} placeholder="Enter your observations, actions, statements, evidence, medical response, notifications, and other confirmed details. Unknown information may remain unknown." />
              <small>{fieldNotes.length.toLocaleString()} of 50,000 characters</small>
            </label>
            <div className="iw-note-guidance"><strong>Write what is known.</strong><span>The system will identify missing information without inventing facts.</span></div>
            <div className="iw-wizard-actions"><button className="iw-button iw-button-secondary" type="button" onClick={() => setStep(0)}>Back</button><button className="iw-button iw-button-gold" type="button" onClick={() => void saveNotesAndContinue()}>Save and Review Facts</button></div>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="iw-wizard-content">
            <div className="iw-section-intro"><h3>Review the extracted facts</h3><p>Confirm, correct, or leave information unknown before it can populate an official form.</p></div>
            <div className="iw-fact-grid">
              <label className="iw-field"><span>Category</span><input value={category || incident?.category || ""} onChange={(event) => { setCategory(event.target.value); markUnsaved(); }} /></label>
              <label className="iw-field"><span>Location</span><input value={location || incident?.location || ""} onChange={(event) => { setLocation(event.target.value); markUnsaved(); }} /></label>
              {Object.entries(facts).map(([key, value]) => <label className="iw-field" key={key}><span>{key.replaceAll("_", " ")}</span><input value={displayValue(value)} onChange={(event) => { setFacts((current) => ({ ...current, [key]: event.target.value })); markUnsaved(); }} /></label>)}
            </div>
            {!Object.keys(facts).length ? <div className="iw-callout iw-callout-info"><div><strong>No extracted facts have been saved yet</strong><p>You may review the entered incident details now, or run classification and extraction.</p></div><button className="iw-button iw-button-secondary" type="button" onClick={() => void startJob("extract")}>Review Notes</button></div> : null}
            <div className="iw-wizard-actions"><button className="iw-button iw-button-secondary" type="button" onClick={() => setStep(1)}>Back to Notes</button><button className="iw-button iw-button-gold" type="button" onClick={() => void confirmFacts()}>Confirm Facts and Continue</button></div>
          </div>
        ) : null}

        {step === 3 ? (
          <div className="iw-wizard-content">
            <div className="iw-section-intro"><h3>Resolve missing information</h3><p>Answer what is available. Use “Unknown” or “N/A” when that is the accurate answer.</p></div>
            <div className="iw-form-grid">
              <label className="iw-field"><span>Medical disposition</span><input value={gapAnswers.medical_disposition} onChange={(event) => { setGapAnswers((current) => ({ ...current, medical_disposition: event.target.value })); markUnsaved(); }} placeholder="Seen by infirmary, refused, none reported, unknown…" /></label>
              <label className="iw-field"><span>Photo or video obtained</span><input value={gapAnswers.photo_video_obtained} onChange={(event) => { setGapAnswers((current) => ({ ...current, photo_video_obtained: event.target.value })); markUnsaved(); }} placeholder="Yes, no, unknown, N/A" /></label>
              <label className="iw-field"><span>Drug-test disposition</span><input value={gapAnswers.drug_test_disposition} onChange={(event) => { setGapAnswers((current) => ({ ...current, drug_test_disposition: event.target.value })); markUnsaved(); }} placeholder="Completed, refused, unknown, N/A" /></label>
              {category.toLowerCase().includes("contraband") ? <><label className="iw-field"><span>Evidence description</span><input value={gapAnswers.evidence_description ?? ""} onChange={(event) => { setGapAnswers((current) => ({ ...current, evidence_description: event.target.value })); markUnsaved(); }} /></label><label className="iw-field"><span>Recovery location</span><input value={gapAnswers.recovery_location ?? ""} onChange={(event) => { setGapAnswers((current) => ({ ...current, recovery_location: event.target.value })); markUnsaved(); }} /></label></> : null}
            </div>
            <p className="iw-muted-line">{missingCount ? `${missingCount} standard answer${missingCount === 1 ? "" : "s"} remain blank.` : "Standard missing-information questions are answered."}</p>
            <div className="iw-wizard-actions"><button className="iw-button iw-button-secondary" type="button" onClick={() => setStep(2)}>Back to Facts</button><button className="iw-button iw-button-gold" type="button" onClick={() => void saveMissingInformation()}>Save and Continue to Reports</button></div>
          </div>
        ) : null}

        {step === 4 ? (
          <div className="iw-wizard-content">
            <div className="iw-section-intro"><h3>Generate and review reports</h3><p>Reports remain editable and revisioned. Copy-only outputs will not be converted into printable substitutes.</p></div>
            {jobMessage ? <div className="iw-callout iw-callout-info" role="status"><p>{jobMessage}</p></div> : null}
            <div className="iw-report-preparation-grid">
              {reports.map((report) => <article key={report.report_id} className="iw-mini-document"><span>{report.presentation === "copy_text" ? "Copy" : "Document"}</span><strong>{report.report_type.replaceAll("_", " ")}</strong><small>{report.reporting_officer.display_name}</small></article>)}
              {!reports.length ? <div className="iw-empty-inline"><strong>No reports have been generated yet.</strong><p>Your saved notes and reviewed facts are ready.</p></div> : null}
            </div>
            <div className="iw-wizard-actions"><button className="iw-button iw-button-secondary" type="button" onClick={() => void startJob("generate")}>Generate Reports</button><button className="iw-button iw-button-gold" type="button" onClick={() => void preparePaperwork()}>Continue to Forms & Export</button></div>
          </div>
        ) : null}

        {step === 5 ? (
          <div className="iw-wizard-content">
            <div className="iw-section-intro"><h3>Forms & Export</h3><p>The checklist has organized required, recommended, additional, and physical-only paperwork for this incident.</p></div>
            <div className="iw-packet-summary">
              {(["required", "recommended", "additional"] as const).map((group) => <article key={group}><span>{group}</span><strong>{packet.filter((item) => item.packet_group === group && item.packet_state === "selected").length}</strong><small>selected item(s)</small></article>)}
              <article><span>Physical</span><strong>{packet.filter((item) => item.presentation === "physical").length}</strong><small>handwritten reminder(s)</small></article>
            </div>
            {incident ? <div className="iw-completion-panel"><div><strong>{incident.incident_number || "Unnumbered Incident"}</strong><p>{incident.incident_name || "Incident name not assigned"}</p></div><Link className="iw-button iw-button-gold" to={`/reports/${incident.incident_id}`}>Open Document Studio</Link></div> : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}
