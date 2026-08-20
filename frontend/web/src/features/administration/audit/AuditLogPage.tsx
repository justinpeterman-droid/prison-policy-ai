import { useEffect, useMemo, useState } from "react";
import { listAdminAudit, type AdminAuditEvent } from "../api";

function labelAction(value: string): string {
  return value.replaceAll(".", " · ").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function AuditLogPage() {
  const [actionFamily, setActionFamily] = useState("");
  const [result, setResult] = useState("");
  const [events, setEvents] = useState<AdminAuditEvent[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void listAdminAudit({ actionFamily: actionFamily || undefined, result: result || undefined })
      .then((page) => { if (active) setEvents(page.items); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Audit events could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [actionFamily, reload, result]);

  const selected = useMemo(() => events.find((event) => event.eventId === selectedId) ?? null, [events, selectedId]);

  return (
    <div className="admin-page">
      <header className="admin-page-header"><div><p className="admin-kicker">Administration</p><h1>Audit Log</h1><p>Read-only activity history with safe metadata only. Report narratives, credentials, PINs, and tokens are excluded.</p></div><button className="admin-secondary-button" type="button" onClick={() => setReload((value) => value + 1)}>Refresh</button></header>

      <section className="admin-filter-bar compact" aria-label="Audit filters">
        <label className="admin-filter-select">Action family<select value={actionFamily} onChange={(event) => setActionFamily(event.target.value)}><option value="">All actions</option><option value="admin">Admin</option><option value="incident">Incident</option><option value="report">Report</option><option value="account">Account</option></select></label>
        <label className="admin-filter-select">Result<select value={result} onChange={(event) => setResult(event.target.value)}><option value="">All results</option><option value="success">Success</option><option value="denied">Denied</option><option value="failed">Failed</option></select></label>
      </section>

      {loading ? <section className="admin-loading-panel" aria-busy="true">Loading immutable audit events…</section> : null}
      {error ? <section className="admin-alert error" role="alert">{error}</section> : null}
      {!loading && !error ? (
        <div className="admin-audit-layout">
          <section className="admin-table-shell admin-audit-table" aria-label="Audit events">
            <div className="admin-table-header admin-audit-grid"><span>Time</span><span>Action</span><span>Result</span><span>Target</span><span aria-hidden="true" /></div>
            {events.map((event) => (
              <button className={`admin-table-row admin-audit-grid ${event.eventId === selectedId ? "is-selected" : ""}`} type="button" key={event.eventId} onClick={() => setSelectedId(event.eventId)}>
                <span>{new Date(event.occurredAt).toLocaleString()}</span><span className="admin-cell-primary"><strong>{labelAction(event.action)}</strong><small>Request {event.requestId}</small></span><span><em className={`admin-records-status ${event.result}`}>{event.result}</em></span><span>{event.targetType ?? "—"}</span><span className="admin-row-arrow" aria-hidden="true">›</span>
              </button>
            ))}
            {!events.length ? <div className="admin-empty-row">No audit events match these filters.</div> : null}
          </section>

          {selected ? (
            <aside className="admin-audit-drawer" aria-label="Audit event details">
              <div className="admin-panel-heading"><div><p>Immutable event</p><h2>{labelAction(selected.action)}</h2></div><button className="admin-text-button" type="button" onClick={() => setSelectedId(null)}>Close</button></div>
              <dl className="admin-detail-list"><div><dt>Occurred</dt><dd>{new Date(selected.occurredAt).toLocaleString()}</dd></div><div><dt>Result</dt><dd>{selected.result}</dd></div><div><dt>Request reference</dt><dd>{selected.requestId}</dd></div><div><dt>Target type</dt><dd>{selected.targetType ?? "None"}</dd></div><div><dt>Target ID</dt><dd>{selected.targetId ?? "None"}</dd></div></dl>
              <div className="admin-safe-details"><h3>Safe details</h3>{Object.keys(selected.details).length ? <dl>{Object.entries(selected.details).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{Array.isArray(value) ? value.join(", ") : String(value)}</dd></div>)}</dl> : <p>No additional safe details are available for this event.</p>}</div>
            </aside>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
