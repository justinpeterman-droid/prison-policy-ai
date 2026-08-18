import { Link } from "react-router-dom";
import "./App.css";

type IconName =
  | "home"
  | "new-report"
  | "reports"
  | "policy"
  | "forms"
  | "account"
  | "clipboard"
  | "count"
  | "message"
  | "documents"
  | "clock"
  | "folder"
  | "file"
  | "check"
  | "headset"
  | "shield"
  | "people"
  | "handshake"
  | "star"
  | "chevron";

interface IconProps {
  name: IconName;
  className?: string;
}

function Icon({ name, className }: IconProps) {
  const shared = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.9,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  let paths: React.ReactNode;
  switch (name) {
    case "home":
      paths = (
        <>
          <path d="m3 11 9-8 9 8" />
          <path d="M5 10v10h14V10" />
          <path d="M9 20v-6h6v6" />
        </>
      );
      break;
    case "new-report":
      paths = (
        <>
          <path d="M7 3h8l4 4v14H7z" />
          <path d="M15 3v5h5" />
          <path d="M10 13h6M13 10v6" />
        </>
      );
      break;
    case "reports":
    case "folder":
      paths = (
        <>
          <path d="M3 7h7l2 2h9v10H3z" />
          <path d="M3 7V5h7l2 2" />
        </>
      );
      break;
    case "policy":
      paths = (
        <>
          <path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z" />
          <path d="M9 12h6M12 9v6" />
        </>
      );
      break;
    case "forms":
    case "file":
      paths = (
        <>
          <path d="M6 3h9l3 3v15H6z" />
          <path d="M15 3v4h4M9 11h6M9 15h6" />
        </>
      );
      break;
    case "account":
      paths = (
        <>
          <circle cx="12" cy="8" r="4" />
          <path d="M4 21c.8-4.3 3.5-6.5 8-6.5s7.2 2.2 8 6.5" />
        </>
      );
      break;
    case "clipboard":
      paths = (
        <>
          <path d="M8 5H5v16h14V5h-3" />
          <rect x="8" y="2.5" width="8" height="5" rx="2" />
          <path d="M9 12h6M9 16h4" />
        </>
      );
      break;
    case "count":
      paths = (
        <>
          <rect x="4" y="3" width="16" height="18" rx="2" />
          <path d="M8 7h8M8 11h2M14 11h2M8 15h2M14 15h2" />
        </>
      );
      break;
    case "message":
      paths = (
        <>
          <path d="M4 5h16v11H9l-5 4z" />
          <path d="M9 10h.01M12 10h.01M15 10h.01" />
        </>
      );
      break;
    case "documents":
      paths = (
        <>
          <path d="M8 3h10v14H8z" />
          <path d="M5 7H3v14h10v-2M11 7h4M11 11h4" />
        </>
      );
      break;
    case "clock":
      paths = (
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v6l4 2" />
        </>
      );
      break;
    case "check":
      paths = <path d="m5 12 4 4L19 6" />;
      break;
    case "headset":
      paths = (
        <>
          <path d="M4 13v-2a8 8 0 0 1 16 0v2" />
          <path d="M4 13h3v6H5a2 2 0 0 1-2-2v-2a2 2 0 0 1 1-2ZM20 13h-3v6h2a2 2 0 0 0 2-2v-2a2 2 0 0 0-1-2Z" />
        </>
      );
      break;
    case "shield":
      paths = (
        <>
          <path d="M12 3 4.5 6v5.5c0 4.7 2.9 8 7.5 9.5 4.6-1.5 7.5-4.8 7.5-9.5V6z" />
          <path d="m8.5 12 2.2 2.2 4.8-5" />
        </>
      );
      break;
    case "people":
      paths = (
        <>
          <circle cx="9" cy="8" r="3" />
          <circle cx="17" cy="9" r="2.5" />
          <path d="M3.5 20c.7-3.8 2.5-5.7 5.5-5.7s4.8 1.9 5.5 5.7M14 15.2c3.4-.6 5.5 1 6.5 4.8" />
        </>
      );
      break;
    case "handshake":
      paths = (
        <>
          <path d="m3 9 4-4 4 2-5 6zM21 9l-4-4-4 2 5 6z" />
          <path d="m8 11 5 5c1 1 2.5-.5 1.5-1.5l-3-3M13 16l1 1c1 1 2.5-.5 1.5-1.5M7 13l4 4c1 1 2.5-.5 1.5-1.5" />
        </>
      );
      break;
    case "star":
      paths = <path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-2.9-5.6 2.9 1.1-6.2L3 9.6l6.2-.9z" />;
      break;
    case "chevron":
      paths = <path d="m9 5 7 7-7 7" />;
      break;
    default:
      paths = null;
  }

  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
      {...shared}
    >
      {paths}
    </svg>
  );
}

function BrandMark() {
  return (
    <svg viewBox="0 0 72 84" role="img" aria-label="S.L.U.T. shield">
      <defs>
        <linearGradient id="shieldGold" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#f8dc8b" />
          <stop offset="0.5" stopColor="#d09a30" />
          <stop offset="1" stopColor="#8f590f" />
        </linearGradient>
        <linearGradient id="shieldNavy" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#174f80" />
          <stop offset="1" stopColor="#071f38" />
        </linearGradient>
      </defs>
      <path d="M36 3 66 14v28c0 19-11.6 31.5-30 39C17.6 73.5 6 61 6 42V14z" fill="url(#shieldGold)" />
      <path d="M36 8 60 17v24c0 15.5-8.9 26.3-24 33-15.1-6.7-24-17.5-24-33V17z" fill="url(#shieldNavy)" />
      <path d="M24 28c7 2 11 5 12 11 1-6 5-9 12-11-2 8-6 13-12 16-6-3-10-8-12-16Z" fill="#f3ce73" />
      <path d="M36 39v20M27 51h18" fill="none" stroke="#f3ce73" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

const navigation = [
  { label: "Home", icon: "home" as const, to: "/workspace" },
  { label: "New Report", icon: "new-report" as const, to: "/workspace/new-report" },
  { label: "Reports", icon: "reports" as const, to: "/workspace/reports" },
  { label: "Policy Expert", icon: "policy" as const, to: "/workspace/policy-expert" },
  { label: "Forms Library", icon: "forms" as const, to: "/workspace/forms" },
  { label: "Account", icon: "account" as const, to: "/workspace/account" },
];

const actions = [
  {
    title: "Start New Incident",
    description: "Create a guided report with required forms.",
    icon: "clipboard" as const,
    button: "Start",
    to: "/workspace/new-report",
  },
  {
    title: "Open Count Sheet",
    description: "NCU Days Count — fill out, reconcile, and print.",
    icon: "count" as const,
    button: "Open",
    to: "/workspace/count-sheet",
  },
  {
    title: "Ask a Policy Question",
    description: "Search policies and get grounded answers with citations.",
    icon: "message" as const,
    button: "Ask",
    to: "/workspace/policy-expert",
  },
  {
    title: "Open Forms Library",
    description: "Browse, preview, and print approved department forms.",
    icon: "documents" as const,
    button: "Browse",
    to: "/workspace/forms",
  },
];

const recentIncidents = [
  { number: "2026-08-028", name: "East Hall Contraband", status: "Needs information", tone: "warning" },
  { number: "2026-08-027", name: "Intake Staff Assault", status: "Ready to review", tone: "" },
  { number: "2026-08-026", name: "Cell 112 Disturbance", status: "Complete", tone: "complete" },
];

const frequentlyUsedForms = [
  "005/409 Incident Report",
  "Cover Letter",
  "Supervisor Summary",
  "Uniform Inspection Log",
  "Perimeter Check List",
];

const checklist = [
  "Complete Assignment Roster",
  "Complete Uniform Inspection Log",
  "Open Count Sheet",
];

function Panel({
  title,
  icon,
  action,
  children,
  className = "",
}: {
  title: string;
  icon: IconName;
  action?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`.trim()}>
      <header className="panel-header">
        <h2 className="panel-title">
          <Icon name={icon} />
          {title}
        </h2>
        {action ? (
          <Link className="panel-action" to="#" aria-label={`${action} ${title}`}>
            {action} →
          </Link>
        ) : null}
      </header>
      <div className="panel-content">{children}</div>
    </section>
  );
}

export function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Application navigation">
        <div className="brand">
          <div className="brand-mark">
            <BrandMark />
          </div>
          <div className="brand-copy">
            <p className="brand-title">S.L.U.T.</p>
            <p className="brand-subtitle">Standard Logistics &amp; Unit Tools</p>
          </div>
        </div>

        <nav className="primary-navigation" aria-label="Officer workspace">
          {navigation.map((item, index) => (
            <Link
              key={item.label}
              className="navigation-link"
              to={item.to}
              aria-label={item.label}
              aria-current={index === 0 ? "page" : undefined}
            >
              <Icon name={item.icon} className="navigation-icon" />
              <span className="navigation-label">{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-status">
            <div className="sidebar-status-row">
              <span className="online-dot" />
              <span>
                <strong>System Online</strong>
                All systems operational
              </span>
            </div>
            <div className="sidebar-status-row">
              <Icon name="headset" className="navigation-icon" />
              <span>
                <strong>Need Help?</strong>
                Open support guidance
              </span>
            </div>
          </div>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div className="topbar-status">
            <span className="online-dot" />
            Online
          </div>
          <div className="topbar-status">
            <Icon name="check" className="navigation-icon" />
            Last synced 2 minutes ago
          </div>
          <span className="topbar-divider" />
          <button className="profile-control" type="button" aria-label="Open account menu">
            <span className="avatar" aria-hidden="true">OM</span>
            Officer Morgan
            <Icon name="chevron" className="navigation-icon" />
          </button>
        </header>

        <main className="dashboard">
          <section className="hero" aria-labelledby="dashboard-heading">
            <div className="hero-copy">
              <p className="hero-kicker">Good afternoon,</p>
              <h1 className="hero-title" id="dashboard-heading">Officer Morgan</h1>
              <div className="hero-meta">
                <span>Monday, August 18, 2026</span>
                <span>Day Shift</span>
              </div>
            </div>
            <div className="hero-values" aria-hidden="true">
              <span>Professionalism</span><i />
              <span>Accountability</span><i />
              <span>Integrity</span>
            </div>
          </section>

          <section className="action-grid" aria-label="Primary daily actions">
            {actions.map((action) => (
              <article className="action-card" key={action.title}>
                <div className="action-icon-fixture">
                  <Icon name={action.icon} />
                </div>
                <div className="action-copy">
                  <h2>{action.title}</h2>
                  <p>{action.description}</p>
                </div>
                <Link className="action-link" to={action.to} aria-label={action.title}>
                  <span>{action.button}</span>
                  <span aria-hidden="true">→</span>
                </Link>
              </article>
            ))}
          </section>

          <section className="dashboard-grid" aria-label="Current work and resources">
            <Panel title="Continue Your Work" icon="clock">
              <div className="continue-card">
                <span className="incident-number">2026-08-029</span>
                <span className="incident-name">Barracks 4 Fight</span>
                <span className="incident-meta">Last edited 18 minutes ago</span>
                <div className="progress-row">
                  <Link
                    className="secondary-button"
                    to="/workspace/reports/current"
                    aria-label="Continue current incident"
                  >
                    Continue →
                  </Link>
                  <span className="status-badge">Ready to review</span>
                </div>
              </div>
            </Panel>

            <Panel title="Recent Incidents" icon="file" action="View all">
              <ul className="list">
                {recentIncidents.map((incident) => (
                  <li className="list-row" key={incident.number}>
                    <span className="row-id">{incident.number}</span>
                    <span className="row-name">{incident.name}</span>
                    <span className={`status-badge ${incident.tone}`.trim()}>{incident.status}</span>
                  </li>
                ))}
              </ul>
            </Panel>

            <Panel title="Frequently Used Forms" icon="folder" action="View all">
              <ul className="list">
                {frequentlyUsedForms.map((form) => (
                  <li className="form-row" key={form}>
                    <Icon name="file" />
                    <span>{form}</span>
                    <Icon name="chevron" className="chevron" />
                  </li>
                ))}
              </ul>
            </Panel>

            <Panel title="Quick Access" icon="folder" className="quick-access">
              <div className="quick-list">
                <Link className="quick-link" to="/workspace/reports" aria-label="View report library">
                  <Icon name="reports" /> View My Reports <Icon name="chevron" className="chevron" />
                </Link>
                <Link className="quick-link" to="/workspace/forms" aria-label="Open forms from quick access">
                  <Icon name="forms" /> Open Forms Library <Icon name="chevron" className="chevron" />
                </Link>
                <Link className="quick-link" to="/workspace/policy-expert" aria-label="Open policy expert from quick access">
                  <Icon name="policy" /> Policy Expert <Icon name="chevron" className="chevron" />
                </Link>
                <Link className="quick-link" to="/workspace/count-sheet" aria-label="Open count sheet from quick access">
                  <Icon name="count" /> Open Count Sheet <Icon name="chevron" className="chevron" />
                </Link>
                <Link className="quick-link" to="/workspace/admin/paperwork" aria-label="Open daily paperwork">
                  <Icon name="clipboard" /> Daily Paperwork <Icon name="chevron" className="chevron" />
                </Link>
              </div>
            </Panel>
          </section>

          <section className="bottom-grid" aria-label="Daily support information">
            <Panel title="Your Daily Checklist" icon="clipboard">
              <div>
                {checklist.map((item) => (
                  <div className="checklist-row" key={item}>
                    <span className="check-circle" />
                    <span>{item}</span>
                    <button className="secondary-button" type="button">Open</button>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel title="Quick Links" icon="handshake">
              <div className="quick-list">
                <Link className="quick-link" to="/workspace/forms" aria-label="Go to forms library">
                  <Icon name="forms" /> Forms Library <Icon name="chevron" className="chevron" />
                </Link>
                <Link className="quick-link" to="/workspace/policy-expert" aria-label="Go to policy expert">
                  <Icon name="policy" /> Policy Expert <Icon name="chevron" className="chevron" />
                </Link>
                <Link className="quick-link" to="/workspace/account" aria-label="Go to my account">
                  <Icon name="account" /> My Account <Icon name="chevron" className="chevron" />
                </Link>
              </div>
            </Panel>

            <Panel title="Recent Activity" icon="clock" action="View all">
              <div>
                {[
                  ["Incident report updated", "18 min ago"],
                  ["Policy question answered", "42 min ago"],
                  ["005/409 form viewed", "1 hr ago"],
                  ["Count sheet opened", "2 hr ago"],
                ].map(([activity, time]) => (
                  <div className="activity-row" key={activity}>
                    <span className="activity-dot" />
                    <span>{activity}</span>
                    <span className="activity-time">{time}</span>
                  </div>
                ))}
              </div>
            </Panel>
          </section>

          <footer className="trust-strip">
            <div className="quote">“Discipline is the bridge between goals and accomplishment.”</div>
            <div className="trust-value"><Icon name="shield" /> Security</div>
            <div className="trust-value"><Icon name="people" /> Service</div>
            <div className="trust-value"><Icon name="handshake" /> Teamwork</div>
            <div className="trust-value"><Icon name="star" /> Excellence</div>
            <time className="current-time" dateTime="2026-08-18T15:42:00">
              Mon, Aug 18, 2026<br />3:42 PM
            </time>
          </footer>
        </main>
      </div>
    </div>
  );
}
