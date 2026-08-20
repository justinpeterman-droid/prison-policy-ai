import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import heroMobile from "../../assets/operations-horizon-v4-mobile.webp";
import heroTablet from "../../assets/operations-horizon-v4-tablet.webp";
import heroDesktop from "../../assets/operations-horizon-v4.webp";
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

const HOME_HERO_PRELOADS = [
  { href: heroDesktop, media: "(min-width: 1440px)" },
  { href: heroTablet, media: "(min-width: 761px) and (max-width: 1439px)" },
  { href: heroMobile, media: "(max-width: 760px)" },
] as const;

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
    title: "New Incident Report",
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

type ActionIconName = "report" | "count" | "policy" | "forms";

function ActionIcon({ name }: { name: ActionIconName }) {
  const common = { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };
  if (name === "report") return <svg {...common}><path d="M6 3h9l4 4v14H6z"/><path d="M15 3v5h5M9 13h6M12 10v6"/></svg>;
  if (name === "count") return <svg {...common}><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 3v18M15 9v12M9 15h12"/></svg>;
  if (name === "policy") return <svg {...common}><path d="M12 3 5 6v5c0 4.8 2.8 8.2 7 10 4.2-1.8 7-5.2 7-10V6z"/><path d="M9.6 10a2.5 2.5 0 1 1 3.4 2.3c-.7.3-1 .8-1 1.4M12 17h.01"/></svg>;
  return <svg {...common}><path d="M3 6.5h6l2 2h10v10.5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 10h18"/></svg>;
}

function ChevronRight() {
  return <svg className="officer-home-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>;
}

function greetingForNow(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning,";
  if (hour < 18) return "Good afternoon,";
  return "Good evening,";
}

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
    const links = HOME_HERO_PRELOADS.map(({ href, media }) => {
      const link = document.createElement("link");
      link.rel = "preload";
      link.as = "image";
      link.type = "image/webp";
      link.href = href;
      link.media = media;
      link.setAttribute("fetchpriority", "high");
      link.dataset.gowHomeHeroPreload = "true";
      document.head.append(link);
      return link;
    });
    return () => links.forEach((link) => link.remove());
  }, []);

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
          <p>{greetingForNow()}</p>
          <h1 id="officer-home-heading">{profile.displayName}</h1>
          <span>{shift ? `${shift} Shift` : "Shift not assigned"}</span>
          <p className="officer-home-message">Stay safe. Stay focused. Your work stays organized here.</p>
        </div>
        <div className="officer-home-values" aria-label="Professional values">
          <span>Professionalism</span><span>•</span><span>Accountability</span><span>•</span><span>Integrity</span>
        </div>
      </section>

      <div className="officer-home-layout">
        <div className="officer-home-main-column">
      <section className="officer-home-actions" aria-label="Primary actions">
        {PRIMARY_ACTIONS.map((item, index) => (
          <article className="officer-home-action-card" key={item.title}>
            <div className="officer-home-action-icon" aria-hidden="true"><ActionIcon name={("report count policy forms".split(" ") as ActionIconName[])[index]} /></div>
            <h2>{item.title}</h2>
            <p>
              {item.description}
              {index === 1 && !loading && !error && summary ? (
                <span className="officer-home-action-state">
                  {summary.countSheet ? `Saved · Revision ${summary.countSheet.revision}` : "Not started"}
                </span>
              ) : null}
            </p>
            <Link
              className={index === 0 ? "officer-home-action-link primary" : "officer-home-action-link"}
              to={item.href}
              aria-label={item.title}
            >
              {item.action}<ChevronRight />
            </Link>
          </article>
        ))}
      </section>

      {loading ? (
        <section className="officer-home-state loading" aria-busy="true" aria-label="Loading your authorized work">
          <span className="officer-home-visually-hidden">Loading your authorized work…</span>
          <div className="officer-home-skeleton" aria-hidden="true">
            <span /><span /><span /><span />
          </div>
        </section>
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
                    <dd><time dateTime={summary.continueIncident.updatedAt}>{formatRelative(summary.continueIncident.updatedAt)}</time></dd>
                  </div>
                </dl>
                <Link
                  className="officer-home-continue-link"
                  to={`/reports/${summary.continueIncident.incidentId}`}
                >
                  Continue incident <ChevronRight />
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
                      <ChevronRight />
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
                      <ChevronRight />
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
                  <p>Last saved <time dateTime={summary.countSheet.updatedAt}>{formatRelative(summary.countSheet.updatedAt)}</time>.</p>
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

        <aside className="officer-home-utility" aria-label="Quick access">
          <section className="officer-home-utility-panel">
            <h2>Quick Access</h2>
            <nav aria-label="Home shortcuts">
              <Link to="/reports"><ActionIcon name="report" /><span>View My Reports</span><ChevronRight /></Link>
              <Link to="/forms"><ActionIcon name="forms" /><span>Open Forms Library</span><ChevronRight /></Link>
              <Link to="/policy-expert"><ActionIcon name="policy" /><span>Policy Expert</span><ChevronRight /></Link>
              <Link to="/count-sheet"><ActionIcon name="count" /><span>Open Count Sheet</span><ChevronRight /></Link>
            </nav>
          </section>
        </aside>
      </div>
    </div>
  );
}
