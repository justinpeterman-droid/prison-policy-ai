import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { InterfaceIcon } from "../../../components/InterfaceIcon";
import { getAdminOverview, type AdminOverview } from "../api";

function formatTime(value: string | null): string {
  if (!value) return "Not started";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Saved" : parsed.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function humanizeAction(value: string): string {
  return value.replace(/^admin\./, "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function StatusMark({ value }: { value: string }) {
  const normalized = value.toLowerCase().replaceAll(" ", "-");
  return <span className={`admin-status-mark ${normalized}`}>{value}</span>;
}

export function AdminOverviewPage() {
  const [data, setData] = useState<AdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setError(null);
    void getAdminOverview()
      .then((value) => { if (active) setData(value); })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Administrator overview could not be loaded.");
      });
    return () => { active = false; };
  }, [reload]);

  return (
    <div className="admin-page admin-overview-page">
      <header className="admin-page-header admin-command-header">
        <div>
          <p className="admin-kicker">Administration</p>
          <h1>Operational Command Center</h1>
          <p>Today’s operational picture, without burying the work under charts or technical noise.</p>
        </div>
        <div className="admin-command-badge" aria-label="Administrator context">
          <span aria-hidden="true">◆</span>
          <div><strong>Administrator context</strong><small>Actions are individually attributed</small></div>
        </div>
      </header>

      {error ? (
        <section className="admin-alert error" role="alert">
          <div><strong>Command Center unavailable</strong><span>{error}</span></div>
          <button type="button" className="admin-secondary-button" onClick={() => setReload((value) => value + 1)}>Try again</button>
        </section>
      ) : null}

      {!data && !error ? <section className="admin-loading-panel" aria-busy="true">Loading today’s operational picture…</section> : null}

      {data ? (
        <>
          <section className="admin-section" aria-labelledby="todays-paperwork-heading">
            <div className="admin-section-heading">
              <div><p>Current shift</p><h2 id="todays-paperwork-heading">Today’s Paperwork</h2></div>
              <Link to="/admin/paperwork">Open Paperwork Center <InterfaceIcon name="arrow-right" /></Link>
            </div>
            <div className="admin-paperwork-strip">
              {[
                ["Assignment Roster", data.todaysPaperwork.assignmentRoster],
                ["Uniform Inspection", data.todaysPaperwork.uniformInspection],
              ].map(([label, item]) => {
                const record = item as AdminOverview["todaysPaperwork"]["assignmentRoster"];
                return (
                  <article className="admin-paperwork-fixture" key={label as string}>
                    <div className="admin-paperwork-icon"><InterfaceIcon name="paperwork" /></div>
                    <div><h3>{label as string}</h3><p>{record.status === "saved" ? `Saved ${formatTime(record.updatedAt)}` : "Not started"}</p></div>
                    <StatusMark value={record.status === "saved" ? "Saved" : "Not started"} />
                  </article>
                );
              })}
            </div>
          </section>

          <div className="admin-overview-grid">
            <section className="admin-panel admin-attention-panel" aria-labelledby="attention-heading">
              <div className="admin-panel-heading"><div><p>Review queue</p><h2 id="attention-heading">Incidents Needing Attention</h2></div><Link to="/admin/incidents">View all</Link></div>
              {data.incidentsNeedingAttention.length ? (
                <ul className="admin-attention-list">
                  {data.incidentsNeedingAttention.map((incident) => (
                    <li key={incident.incidentId}>
                      <Link to={`/admin/incidents?open=${incident.incidentId}`}>
                        <div className="admin-incident-identity"><strong>{incident.incidentNumber ?? "Unnumbered Incident"}</strong><span>{incident.incidentName ?? "Incident name not entered"}</span></div>
                        <StatusMark value={incident.progress.label} />
                        <div className="admin-row-counts"><span>{incident.reportCount} reports</span><span>{incident.requiredPaperworkCount} required forms</span></div>
                        <span className="admin-row-arrow"><InterfaceIcon name="chevron-right" /></span>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : <div className="admin-empty-row"><strong>No incidents need attention</strong><span>Nothing is being held in a hidden administrator queue.</span></div>}
            </section>

            <section className="admin-panel admin-account-panel" aria-labelledby="account-conditions-heading">
              <div className="admin-panel-heading"><div><p>Identity operations</p><h2 id="account-conditions-heading">Account Conditions</h2></div><Link to="/admin/accounts-staff">Manage staff</Link></div>
              <div className="admin-condition-list">
                <div><span>Locked</span><strong>{data.accountConditions.locked}</strong></div>
                <div><span>Deactivated</span><strong>{data.accountConditions.deactivated}</strong></div>
                <div><span>Temporary PIN</span><strong>{data.accountConditions.temporaryPin}</strong></div>
              </div>
            </section>

            <section className="admin-panel admin-system-panel" aria-labelledby="availability-heading">
              <div className="admin-panel-heading"><div><p>Service readiness</p><h2 id="availability-heading">System Availability</h2></div><Link to="/admin/health">Details</Link></div>
              <ul className="admin-system-list">
                {Object.entries(data.systemAvailability).map(([name, status]) => (
                  <li key={name}><span>{name.replaceAll("_", " ")}</span><StatusMark value={status} /></li>
                ))}
              </ul>
            </section>

            <section className="admin-panel admin-activity-panel" aria-labelledby="admin-activity-heading">
              <div className="admin-panel-heading"><div><p>Safe event summary</p><h2 id="admin-activity-heading">Recent Administrative Activity</h2></div><Link to="/admin/audit">Audit log</Link></div>
              {data.recentAdministrativeActivity.length ? (
                <ul className="admin-activity-list">
                  {data.recentAdministrativeActivity.slice(0, 6).map((event) => (
                    <li key={event.eventId}><span className="admin-activity-dot" aria-hidden="true" /><div><strong>{humanizeAction(event.action)}</strong><small>{event.result}</small></div></li>
                  ))}
                </ul>
              ) : <div className="admin-empty-row">No recent administrator activity.</div>}
            </section>
          </div>
        </>
      ) : null}
    </div>
  );
}
