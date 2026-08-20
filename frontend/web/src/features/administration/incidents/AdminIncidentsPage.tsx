import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { InterfaceIcon } from "../../../components/InterfaceIcon";
import { listRowClassName } from "../../../design-system/Primitives";
import { listAdminIncidents, type AdminIncidentSummary } from "../api";

export function AdminIncidentsPage() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [recordsStatus, setRecordsStatus] = useState("");
  const [items, setItems] = useState<AdminIncidentSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void listAdminIncidents({ q: submittedQuery, recordsStatus: recordsStatus || undefined })
      .then((page) => { if (active) setItems(page.items); })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Incidents could not be loaded.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [submittedQuery, recordsStatus]);

  function submit(event: FormEvent) {
    event.preventDefault();
    setSubmittedQuery(query.trim());
  }

  return (
    <div className="admin-page">
      <header className="admin-page-header">
        <div><p className="admin-kicker">Administration</p><h1>All Incidents</h1><p>Search the facility-wide incident library without changing the officer’s calculated workflow progress.</p></div>
      </header>

      <section className="admin-filter-bar" aria-label="Incident filters">
        <form onSubmit={submit} className="admin-search-form">
          <label htmlFor="admin-incident-search">Search incidents</label>
          <div><input id="admin-incident-search" type="search" placeholder="Incident number, name, officer, location…" value={query} onChange={(event) => setQuery(event.target.value)} /><button className="admin-primary-button" type="submit">Search</button></div>
        </form>
        <label className="admin-filter-select">Records status<select value={recordsStatus} onChange={(event) => setRecordsStatus(event.target.value)}><option value="">All statuses</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="archived">Archived</option></select></label>
      </section>

      {loading ? <section className="admin-loading-panel" aria-busy="true">Loading authorized incidents…</section> : null}
      {error ? <section className="admin-alert error" role="alert">{error}</section> : null}
      {!loading && !error ? (
        <section className="admin-table-shell" aria-label="Administrator incident results">
          <div className="admin-table-header admin-incidents-grid"><span>Incident</span><span>Officer progress</span><span>Records status</span><span>Officers</span><span>Paperwork</span><span aria-hidden="true" /></div>
          {items.length ? items.map((incident) => (
            <Link className={listRowClassName("navigation", "admin-table-row admin-incidents-grid")} key={incident.incidentId} to={`/admin/incidents/${incident.incidentId}`}>
              <span className="admin-cell-primary"><strong>{incident.incidentNumber ?? "Unnumbered Incident"}</strong><small>{incident.incidentName ?? "Incident name not entered"}</small><small>{[incident.category, incident.location].filter(Boolean).join(" · ") || "Details pending"}</small></span>
              <span><em className="admin-soft-status">{incident.progress.label}</em></span>
              <span><em className={`admin-records-status ${incident.recordsStatus}`}>{incident.recordsStatus.replaceAll("_", " ")}</em></span>
              <span>{incident.reportingOfficers.map((person) => person.displayName).join(", ") || "Not assigned"}</span>
              <span>{incident.officerReportCount} reports · {incident.requiredPaperworkCount} required</span>
              <span className="admin-row-arrow"><InterfaceIcon name="chevron-right" /></span>
            </Link>
          )) : <div className="admin-empty-row"><strong>No matching incidents</strong><span>Try a broader search or remove the records-status filter.</span></div>}
        </section>
      ) : null}
    </div>
  );
}
