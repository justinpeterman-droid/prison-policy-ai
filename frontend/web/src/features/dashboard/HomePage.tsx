import { Link } from "react-router-dom";
import type { SessionProfile } from "../auth/api";

const actions = [
  {
    title: "Start New Incident",
    description: "Create a guided report with required forms.",
    label: "Start",
    to: "/new-report",
    icon: "＋",
    primary: true,
  },
  {
    title: "Open Count Sheet",
    description: "NCU Days Count — fill out and print.",
    label: "Open",
    to: "/count-sheet",
    icon: "▦",
  },
  {
    title: "Ask a Policy Question",
    description: "Search policies and receive cited answers.",
    label: "Ask",
    to: "/policy-expert",
    icon: "◇",
  },
  {
    title: "Open Forms Library",
    description: "Browse and print approved department forms.",
    label: "Browse",
    to: "/forms",
    icon: "▤",
  },
];

const recentIncidents = [
  ["2026-08-029", "Barracks 4 Fight", "Ready to review", "18 min ago"],
  ["2026-08-028", "East Hall Contraband", "Needs information", "1 hr ago"],
  ["2026-08-027", "Intake Staff Assault", "Complete", "Yesterday"],
] as const;

const frequentForms = [
  "005/409 Incident Report",
  "Cover Letter",
  "Supervisor Summary",
  "Uniform Inspection Log",
  "Perimeter Check List",
];

export function HomePage({ profile }: { profile: SessionProfile }) {
  return (
    <>
      <section className="gow-hero" aria-labelledby="home-heading">
        <div className="gow-hero-copy">
          <p className="gow-greeting-small">Good afternoon,</p>
          <h1 className="gow-greeting-name" id="home-heading">
            {profile.displayName}
          </h1>
          <p className="gow-incident-meta">
            {profile.shift ? `${profile.shift} Shift` : "Shift not assigned"}
          </p>
          <p className="gow-hero-message">
            Stay safe. Stay focused. You’re making a difference.
          </p>
        </div>
        <div className="gow-hero-values" aria-label="Professional values">
          <span>Professionalism</span><span>•</span><span>Accountability</span><span>•</span><span>Integrity</span>
        </div>
      </section>

      <div className="gow-dashboard-body">
        <section className="gow-action-grid" aria-label="Primary actions">
          {actions.map((action) => (
            <article className="gow-action-card" key={action.title}>
              <div className="gow-action-header">
                <span className="gow-action-icon" aria-hidden="true">{action.icon}</span>
                <div>
                  <h2 className="gow-action-title">{action.title}</h2>
                  <p className="gow-action-description">{action.description}</p>
                </div>
              </div>
              <span />
              <Link
                className={`gow-action-link ${action.primary ? "primary" : ""}`}
                to={action.to}
                aria-label={action.title}
              >
                {action.label}<span aria-hidden="true">›</span>
              </Link>
            </article>
          ))}
        </section>

        <section className="gow-primary-grid" aria-label="Current incident work and forms">
          <article className="gow-panel">
            <div className="gow-panel-heading">
              <div className="gow-panel-heading-main"><span aria-hidden="true">◷</span><h2>Continue Your Work</h2></div>
            </div>
            <div className="gow-continue-card">
              <div className="gow-incident-number">2026-08-029</div>
              <div className="gow-incident-title">Barracks 4 Fight</div>
              <div className="gow-incident-meta">Last edited 18 minutes ago</div>
              <div className="gow-progress-line" aria-label="5 of 6 steps complete"><span /></div>
              <div className="gow-incident-meta">5 of 6 steps complete</div>
              <Link className="gow-continue-action" to="/reports">Continue Incident <span aria-hidden="true">›</span></Link>
            </div>
          </article>

          <article className="gow-panel">
            <div className="gow-panel-heading">
              <div className="gow-panel-heading-main"><span aria-hidden="true">▤</span><h2>Recent Incidents</h2></div>
              <Link className="gow-panel-link" to="/reports">View All</Link>
            </div>
            <ul className="gow-list">
              {recentIncidents.map(([number, name, state, time]) => (
                <li className="gow-list-row" key={number}>
                  <span className="gow-incident-number">{number}</span>
                  <span className="gow-list-title">{name}</span>
                  <span className={`gow-inline-status ${state === "Complete" ? "complete" : state === "Needs information" ? "warning" : ""}`}>{state}</span>
                  <span className="gow-list-time">{time}</span>
                </li>
              ))}
            </ul>
          </article>

          <article className="gow-panel">
            <div className="gow-panel-heading">
              <div className="gow-panel-heading-main"><span aria-hidden="true">▣</span><h2>Frequently Used Forms</h2></div>
              <Link className="gow-panel-link" to="/forms">View All</Link>
            </div>
            <ul className="gow-list">
              {frequentForms.map((form) => (
                <li className="gow-form-row" key={form}>
                  <span className="gow-row-icon" aria-hidden="true">▤</span>
                  <span>{form}</span>
                  <span aria-hidden="true">⌁</span>
                </li>
              ))}
            </ul>
          </article>
        </section>

        <section className="gow-secondary-grid" aria-label="Daily work and activity">
          <article className="gow-panel">
            <div className="gow-panel-heading">
              <div className="gow-panel-heading-main"><span aria-hidden="true">✓</span><h2>Your Daily Checklist</h2></div>
              <span className="gow-panel-link">3 items</span>
            </div>
            <div className="gow-check-row"><span className="gow-check-control" /><span>Complete Assignment Roster</span><Link className="gow-small-button" to="/reports">Open</Link></div>
            <div className="gow-check-row"><span className="gow-check-control" /><span>Complete Uniform Inspection Log</span><Link className="gow-small-button" to="/reports">Open</Link></div>
            <div className="gow-check-row"><span className="gow-check-control" /><span>Open Count Sheet</span><Link className="gow-small-button" to="/count-sheet">Open</Link></div>
          </article>

          <article className="gow-panel">
            <div className="gow-panel-heading"><div className="gow-panel-heading-main"><span aria-hidden="true">⌁</span><h2>Quick Links</h2></div></div>
            {[
              ["Forms Library", "/forms"],
              ["Policy Expert", "/policy-expert"],
              ["My Account", "/account"],
              ["Help & Support", "/help"],
            ].map(([label, to]) => <div className="gow-link-row" key={label}><Link to={to}><span className="gow-row-icon" aria-hidden="true">›</span><span>{label}</span><span aria-hidden="true">›</span></Link></div>)}
          </article>

          <article className="gow-panel">
            <div className="gow-panel-heading"><div className="gow-panel-heading-main"><span aria-hidden="true">◷</span><h2>Recent Activity</h2></div><Link className="gow-panel-link" to="/reports">View All</Link></div>
            {[
              ["Report 2026-08-029 updated", "18 min ago"],
              ["Policy question answered", "42 min ago"],
              ["Form viewed: 005/409", "1 hr ago"],
              ["Count sheet opened", "2 hr ago"],
            ].map(([label, time]) => <div className="gow-activity-row" key={label}><span className="gow-activity-dot" /><span>{label}</span><span className="gow-list-time">{time}</span></div>)}
          </article>
        </section>
      </div>
    </>
  );
}
