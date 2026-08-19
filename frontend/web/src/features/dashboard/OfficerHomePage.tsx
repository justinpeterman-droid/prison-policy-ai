import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { SessionProfile } from "../auth/api";
import {
  fetchOfficerHomeSummary,
  type IncidentHomeSummary,
  type OfficerHomeSummary,
} from "./api";
import "./officer-home.css";

interface OfficerHomePageProps {
  profile: SessionProfile;
  today?: string;
}

function localIsoDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatRelative(value: string): string {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return "Recently updated";
  const minutes = Math.max(0, Math.floor((Date.now() - timestamp) / 60_000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

function IncidentIdentity({ incident }: { incident: IncidentHomeSummary }) {
  return (
    <div className="officer-home-incident-identity">
      <strong>{incident.incidentNumber ?? "Unnumbered Incident"}</strong>
      <span>{incident.incidentName ?? "Incident name not entered"}</span>
    </div>
  );
}

const PRIMARY_ACTIONS = [
  {
    title: "Start New Incident",
    description: "Create a guided report and required paperwork packet.",
    href: "/new-report",
    action: "Start",
  },
  {
    title: "Open Count Sheet",
    description: "Fill out, reconcile, save, and print the NCU Days Count.",
    href: "/count-sheet",
    action: "Open",
  },
  {
    title: "Ask a Policy Question",
    description: "Search approved policy sources and review citations.",
    href: "/policy-expert",
    action: "Ask",
  },
  {
    title: "Open Forms Library",
    description: "Browse approved digital and physical department forms.",
    href: "/forms",
    action: "Browse",
  },
] as const;

export function OfficerHomePage({
  profile,
  today = localIsoDate(),
}: OfficerHomePageProps) {
  const shift = profile.shift?.trim() ?? "";
  const [summary, setSummary] = useState<OfficerHomeSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    if (!shift) {
      setSummary(null);
      setLoading(false);
      setError("A shift has not been assigned to your account.");
      return () => {
        active = false;
      };
    }
    void fetchOfficerHomeSummary(today, shift)
      .then((data) => {
        if (active) setSummary(data);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setSummary(null);
        setError(
          reason instanceof Error
            ? reason.message
            : "Your Home summary could not be loaded.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadToken, shift, today]);

  const recentIncidents = useMemo(() => {
    if (!summary) return [];
    const continuationId = summary.continueIncident?.incidentId;
    const all = summary.recentIncidents;
    if (!continuationId || all.some((item) => item.incidentId === continuationId)) {
      return all;
    }
    return [summary.continueIncident!, ...all].slice(0, 5);
  }, [summary]);

  return (
    <div className="officer-home-page">
      <section className="officer-home-hero" aria-labelledby="officer-home-heading">
        <div>
          <p>Good afternoon,</p>
          <h1 id="officer-home-heading">{profile.displayName}</h1>
          <span>{shift ? `${shift} Shift` : "Shift not assigned"}</span>
          <p className="officer-home-message">Stay safe. Stay focused. Your work stays organized here.</p>
        </div>
        <div className="officer-home-values" aria-label="Professional values">
          <span>Professionalism</span><span>•</span><span>Accountability</span><span>•</span><span>Integrity</span>
        </div>
      </section>

      <section className="officer-home-actions" aria-label="Primary actions">
        {PRIMARY_ACTIONS.map((item, index) => (
          <article className="officer-home-action-card" key={item.title}>
            <div className="officer-home-action-number" aria-hidden="true">0{index + 1}</div>
            <h2>{item.title}</h2>
            <p>{item.description}</p>
            <Link
              className={index === 0 ? "officer-home-action-link primary" : "officer-home-action-link"}
              to={item.href}
              aria-label={item.title}
            >
              {item.action}<span aria-hidden="true">→</span>
            </Link>
          </article>
        ))}
      </section>

      {loading ? (
        <section className="officer-home-state" aria-busy="true">Loading your authorized work…</section>
      ) : null}
      {error ? (
        <section className="officer-home-state error" role="alert">
          <strong>Home summary unavailable</strong>
          <span>{error}</span>
          <button type="button" onClick={() => setReloadToken((value) => value + 1)}>Try again</button>
        </section>
      ) : null}

      {!loading && !error && summary ? (
        <div className="officer-home-work-grid">
          <section className="officer-home-panel continue-panel" aria-labelledby="continue-work-heading">
            <header>
              <div>
                <p>Current priority</p>
                <h2 id="continue-work-heading">Continue Your Work</h2>
              </div>
            </header>
            {summary.continueIncident ? (
              <div className="officer-home-continue-card">
                <IncidentIdentity incident={summary.continueIncident} />
                <span className="officer-home-progress">{summary.continueIncident.progress.label}</span>
                <dl>
                  <div>
                    <dt>Reports</dt>
                    <dd>{summary.continueIncident.officerReportCount}</dd>
                  </div>
                  <div>
                    <dt>Required paperwork</dt>
                    <dd>{summary.continueIncident.requiredPaperworkCount}</dd>
                  </div>
                  <div>
                    <dt>Updated</dt>
                    <dd>{formatRelative(summary.continueIncident.updatedAt)}</dd>
                  </div>
                </dl>
                <Link
                  className="officer-home-continue-link"
                  to={`/reports/${summary.continueIncident.incidentId}`}
                >
                  Continue incident <span aria-hidden="true">→</span>
                </Link>
              </div>
            ) : (
              <div className="officer-home-empty">
                <strong>No unfinished incidents</strong>
                <span>Start a new incident when reportable work occurs.</span>
              </div>
            )}
          </section>

          <section className="officer-home-panel incidents-panel" aria-labelledby="recent-incidents-heading">
            <header>
              <div>
                <p>Authorized records</p>
                <h2 id="recent-incidents-heading">Recent Incidents</h2>
              </div>
              <Link to="/reports">View all</Link>
            </header>
            {recentIncidents.length ? (
              <ul className="officer-home-incident-list">
                {recentIncidents.map((incident) => (
                  <li key={incident.incidentId}>
                    <Link to={`/reports/${incident.incidentId}`}>
                      <IncidentIdentity incident={incident} />
                      <span className="officer-home-progress">{incident.progress.label}</span>
                      <time dateTime={incident.updatedAt}>{formatRelative(incident.updatedAt)}</time>
                      <span aria-hidden="true">›</span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="officer-home-empty">No recent incidents are available.</div>
            )}
          </section>

          <section className="officer-home-panel forms-panel" aria-labelledby="quick-forms-heading">
            <header>
              <div>
                <p>Approved paperwork</p>
                <h2 id="quick-forms-heading">Quick Forms</h2>
              </div>
              <Link to="/forms">View library</Link>
            </header>
            {summary.quickForms.length ? (
              <ul className="officer-home-form-list">
                {summary.quickForms.map((form) => (
                  <li key={form.templateId}>
                    <Link to={`/forms?form=${encodeURIComponent(form.code)}`}>
                      <span>{form.name}</span>
                      <small>{form.outputKind === "physical_only" ? "Physical form guidance" : "Digital form"}</small>
                      <span aria-hidden="true">›</span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="officer-home-empty">No approved quick forms are available.</div>
            )}
          </section>

          <section className="officer-home-panel count-panel" aria-labelledby="daily-count-heading">
            <header>
              <div>
                <p>Today · {shift} Shift</p>
                <h2 id="daily-count-heading">NCU Days Count</h2>
              </div>
            </header>
            <div className="officer-home-count-body">
              {summary.countSheet ? (
                <>
                  <span className="officer-home-count-state">Revision {summary.countSheet.revision}</span>
                  <p>Last saved {formatRelative(summary.countSheet.updatedAt)}.</p>
                  <Link to="/count-sheet">Open today’s Count Sheet</Link>
                </>
              ) : (
                <>
                  <span className="officer-home-count-state new">Not started</span>
                  <p>No Count Sheet has been saved for this date and shift.</p>
                  <Link to="/count-sheet">Start today’s Count Sheet</Link>
                </>
              )}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
