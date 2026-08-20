import { useEffect, useState } from "react";
import { getAdminHealth } from "../api";

interface HealthData {
  checkedAt: string;
  components: Record<string, "Operational" | "Degraded" | "Unavailable">;
  build: Record<string, string>;
  notices: Array<{ component: string; status: "Operational" | "Degraded" | "Unavailable"; message: string }>;
}

function icon(status: string): string {
  if (status === "Operational") return "✓";
  if (status === "Degraded") return "!";
  return "—";
}

export function SystemHealthPage() {
  const [data, setData] = useState<HealthData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setError(null);
    void getAdminHealth()
      .then((value) => { if (active) setData(value as HealthData); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "System health could not be loaded."); });
    return () => { active = false; };
  }, [reload]);

  return (
    <div className="admin-page">
      <header className="admin-page-header"><div><p className="admin-kicker">Administration</p><h1>System Health</h1><p>Operational status only—no secrets, hostnames, credentials, or raw infrastructure errors are exposed here.</p></div><button className="admin-secondary-button" type="button" onClick={() => setReload((value) => value + 1)}>Refresh status</button></header>
      {error ? <section className="admin-alert error" role="alert">{error}</section> : null}
      {!data && !error ? <section className="admin-loading-panel" aria-busy="true">Checking safe operational status…</section> : null}
      {data ? (
        <>
          <section className="admin-health-grid" aria-label="System component health">
            {Object.entries(data.components).map(([name, status]) => (
              <article className={`admin-health-card ${status.toLowerCase()}`} key={name}>
                <span className="admin-health-icon" aria-hidden="true">{icon(status)}</span>
                <div><h2>{name.replaceAll("_", " ")}</h2><span>{status}</span></div>
              </article>
            ))}
          </section>
          <div className="admin-health-lower-grid">
            <section className="admin-panel"><div className="admin-panel-heading"><div><p>Bounded diagnostics</p><h2>Notices</h2></div></div>{data.notices.length ? <ul className="admin-notice-list">{data.notices.map((notice) => <li key={`${notice.component}-${notice.message}`}><span className={`admin-notice-dot ${notice.status.toLowerCase()}`} aria-hidden="true" /><div><strong>{notice.component.replaceAll("_", " ")}</strong><p>{notice.message}</p></div></li>)}</ul> : <div className="admin-empty-row">No degraded notices.</div>}</section>
            <section className="admin-panel"><div className="admin-panel-heading"><div><p>Version references</p><h2>Application Build</h2></div></div><dl className="admin-detail-list">{Object.entries(data.build).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{value}</dd></div>)}<div><dt>Last checked</dt><dd>{new Date(data.checkedAt).toLocaleString()}</dd></div></dl></section>
          </div>
        </>
      ) : null}
    </div>
  );
}
