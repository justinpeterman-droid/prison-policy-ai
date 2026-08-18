import type { ReactNode } from "react";
import "./guided-operations.css";

type IconName =
  | "home"
  | "plus"
  | "folder"
  | "shield"
  | "form"
  | "user"
  | "clipboard"
  | "calendar"
  | "chat"
  | "documents"
  | "clock"
  | "check"
  | "printer"
  | "chevron"
  | "bell"
  | "cloud"
  | "headset"
  | "book"
  | "link"
  | "activity"
  | "menu";

interface IconProps {
  name: IconName;
  className?: string;
}

function Icon({ name, className }: IconProps) {
  const common = {
    className,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (name) {
    case "home":
      return <svg {...common}><path d="m3 11 9-8 9 8"/><path d="M5.5 9.5V21h13V9.5"/><path d="M9.5 21v-7h5v7"/></svg>;
    case "plus":
      return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/></svg>;
    case "folder":
      return <svg {...common}><path d="M3 6.5h6l2 2h10v10.5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 10h18"/></svg>;
    case "shield":
      return <svg {...common}><path d="M12 3 5 6v5c0 4.8 2.8 8.2 7 10 4.2-1.8 7-5.2 7-10V6z"/><path d="m9.2 12.2 1.8 1.8 3.9-4"/></svg>;
    case "form":
      return <svg {...common}><path d="M6 3h9l4 4v14H6z"/><path d="M15 3v5h5M9 12h7M9 16h7"/></svg>;
    case "user":
      return <svg {...common}><circle cx="12" cy="8" r="4"/><path d="M4.5 21c.8-4.2 3.2-6 7.5-6s6.7 1.8 7.5 6"/></svg>;
    case "clipboard":
      return <svg {...common}><path d="M8 5H5v16h14V5h-3"/><rect x="8" y="3" width="8" height="4" rx="2"/><path d="M8 11h8M8 15h5"/></svg>;
    case "calendar":
      return <svg {...common}><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18M7 14h3M14 14h3M7 18h3"/></svg>;
    case "chat":
      return <svg {...common}><path d="M4 5h16v11H9l-5 4z"/><path d="M8 10h.01M12 10h.01M16 10h.01"/></svg>;
    case "documents":
      return <svg {...common}><path d="M8 3h11v15H8z"/><path d="M5 6H3v15h11v-2"/><path d="M11 8h5M11 12h5"/></svg>;
    case "clock":
      return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>;
    case "check":
      return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/></svg>;
    case "printer":
      return <svg {...common}><path d="M7 9V3h10v6M7 18H5a2 2 0 0 1-2-2v-5h18v5a2 2 0 0 1-2 2h-2"/><path d="M7 15h10v6H7z"/></svg>;
    case "chevron":
      return <svg {...common}><path d="m9 6 6 6-6 6"/></svg>;
    case "bell":
      return <svg {...common}><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 8h18c0-1-3-1-3-8"/><path d="M10 21h4"/></svg>;
    case "cloud":
      return <svg {...common}><path d="M7 18h11a4 4 0 0 0 .5-8A7 7 0 0 0 5.2 8.3 5 5 0 0 0 7 18Z"/></svg>;
    case "headset":
      return <svg {...common}><path d="M4 13v-2a8 8 0 0 1 16 0v2"/><path d="M4 13h3v6H5a1 1 0 0 1-1-1zM20 13h-3v6h2a1 1 0 0 0 1-1zM17 19c0 2-2 2-4 2"/></svg>;
    case "book":
      return <svg {...common}><path d="M3 5.5A4.5 4.5 0 0 1 7.5 3H11v16H7.5A4.5 4.5 0 0 0 3 21.5z"/><path d="M21 5.5A4.5 4.5 0 0 0 16.5 3H13v16h3.5a4.5 4.5 0 0 1 4.5 2.5z"/></svg>;
    case "link":
      return <svg {...common}><path d="m10 14 4-4"/><path d="M8.5 16.5 7 18a3.5 3.5 0 1 1-5-5l3-3a3.5 3.5 0 0 1 5 0"/><path d="M15.5 7.5 17 6a3.5 3.5 0 1 1 5 5l-3 3a3.5 3.5 0 0 1-5 0"/></svg>;
    case "activity":
      return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>;
    case "menu":
      return <svg {...common}><path d="M4 7h16M4 12h16M4 17h16"/></svg>;
  }
}

function BrandShield() {
  return <span className="gow-shield" aria-hidden="true"><Icon name="shield" /></span>;
}

const navigation: Array<{ label: string; href: string; icon: IconName }> = [
  { label: "Home", href: "/workspace", icon: "home" },
  { label: "New Report", href: "/workspace/new-report", icon: "plus" },
  { label: "Reports", href: "/workspace/reports", icon: "folder" },
  { label: "Policy Expert", href: "/workspace/policy-expert", icon: "shield" },
  { label: "Forms Library", href: "/workspace/forms", icon: "form" },
  { label: "Account", href: "/workspace/account", icon: "user" },
];

const primaryActions: Array<{
  title: string;
  description: ReactNode;
  label: string;
  href: string;
  icon: IconName;
  iconTone?: "gold" | "paper";
  primary?: boolean;
}> = [
  {
    title: "Start New Incident",
    description: <>Create a guided report<br />with required forms.</>,
    label: "Start",
    href: "/workspace/new-report",
    icon: "clipboard",
    primary: true,
  },
  {
    title: "Open Count Sheet",
    description: <>NCU Days Count<br />Fill out and print.</>,
    label: "Open",
    href: "/workspace/count-sheet",
    icon: "calendar",
    iconTone: "gold",
  },
  {
    title: "Ask a Policy Question",
    description: <>Search policies and<br />get cited answers.</>,
    label: "Ask",
    href: "/workspace/policy-expert",
    icon: "chat",
  },
  {
    title: "Open Forms Library",
    description: <>Browse and print<br />department forms.</>,
    label: "Browse",
    href: "/workspace/forms",
    icon: "documents",
    iconTone: "paper",
  },
];

const recentIncidents = [
  { number: "2026-08-029", name: "Barracks 4 Fight", state: "Ready to review", tone: "ready", time: "18 min ago" },
  { number: "2026-08-028", name: "East Hall Contraband", state: "Needs information", tone: "warning", time: "1 hr ago" },
  { number: "2026-08-027", name: "Intake Staff Assault", state: "Complete", tone: "complete", time: "Yesterday" },
  { number: "2026-08-026", name: "Cell 112 Disturbance", state: "Complete", tone: "complete", time: "Yesterday" },
];

const frequentForms = [
  "005/409 Incident Report",
  "Cover Letter",
  "Supervisor Summary",
  "Uniform Inspection Log",
  "Perimeter Check List",
];

function PanelHeading({ icon, title, action }: { icon: IconName; title: string; action?: ReactNode }) {
  return (
    <div className="gow-panel-heading">
      <div className="gow-panel-heading-main"><Icon name={icon} /><h2>{title}</h2></div>
      {action}
    </div>
  );
}

function StatusBadge({ tone, children }: { tone?: string; children: ReactNode }) {
  return <span className={`gow-inline-status ${tone ?? ""}`.trim()}>{children}</span>;
}

export function App() {
  return (
    <div className="gow-app">
      <aside className="gow-sidebar">
        <div className="gow-brand">
          <BrandShield />
          <div>
            <p className="gow-brand-name">S.L.U.T</p>
            <p className="gow-brand-subtitle">Secure · Logical · Unified · Trusted</p>
          </div>
          <button className="gow-mobile-menu-button" type="button" aria-label="Open navigation menu"><Icon name="menu" /></button>
        </div>

        <nav className="gow-nav" aria-label="Officer navigation">
          {navigation.map((item, index) => (
            <a
              className="gow-nav-link"
              href={item.href}
              key={item.label}
              aria-label={item.label}
              aria-current={index === 0 ? "page" : undefined}
            >
              <span className="gow-nav-icon"><Icon name={item.icon} /></span>
              <span className="gow-nav-label">{item.label}</span>
            </a>
          ))}
        </nav>

        <div className="gow-sidebar-status" aria-label="System status">
          <div className="gow-side-status-line"><span className="gow-side-dot" /> <strong>System Online</strong></div>
          <div className="gow-side-status-line"><Icon name="check" /> All systems operational</div>
          <div className="gow-side-help"><Icon name="headset" /> Need Help?</div>
        </div>

        <div className="gow-sidebar-footer">
          <strong>S.L.U.T</strong>
          <p>Better tools. Safer facilities.</p>
        </div>
      </aside>

      <main className="gow-workspace">
        <header className="gow-topbar" aria-label="Workspace status">
          <div className="gow-status-chip"><span className="gow-online-dot" /><span>Online</span></div>
          <div className="gow-status-chip"><Icon name="cloud" /><span>Last synced 2 minutes ago</span></div>
          <div className="gow-status-chip"><Icon name="check" /><span>All changes saved</span></div>
          <div className="gow-notification" aria-label="2 notifications"><Icon name="bell" /><span className="gow-notification-badge">2</span></div>
          <div className="gow-user-chip"><span className="gow-avatar">OP</span><span>Officer Peterman</span><Icon name="chevron" /></div>
        </header>

        <section className="gow-hero" aria-labelledby="home-heading">
          <div className="gow-hero-copy">
            <p className="gow-greeting-small">Good afternoon,</p>
            <h1 className="gow-greeting-name" id="home-heading">Officer Peterman</h1>
            <p className="gow-hero-message">Stay safe. Stay focused. You’re making a difference.</p>
          </div>
          <div className="gow-hero-values" aria-label="Professional values">
            <span>Professionalism</span><span>•</span><span>Accountability</span><span>•</span><span>Integrity</span>
          </div>
        </section>

        <div className="gow-dashboard-body">
          <section className="gow-action-grid" aria-label="Primary actions">
            {primaryActions.map((action) => (
              <article className="gow-action-card" key={action.title}>
                <div className="gow-action-header">
                  <span className={`gow-action-icon ${action.iconTone ?? ""}`.trim()}><Icon name={action.icon} /></span>
                  <div>
                    <h2 className="gow-action-title">{action.title}</h2>
                    <p className="gow-action-description">{action.description}</p>
                  </div>
                </div>
                <span />
                <a
                  className={`gow-action-link ${action.primary ? "primary" : ""}`.trim()}
                  href={action.href}
                  aria-label={action.title}
                >
                  {action.label}<Icon name="chevron" />
                </a>
              </article>
            ))}
          </section>

          <section className="gow-primary-grid" aria-label="Current incident work and forms">
            <article className="gow-panel">
              <PanelHeading icon="clock" title="Continue Your Work" />
              <div className="gow-continue-card">
                <div className="gow-incident-number">2026-08-029</div>
                <div className="gow-incident-title">Barracks 4 Fight</div>
                <div className="gow-incident-meta">Last edited 18 minutes ago</div>
                <div className="gow-progress-line" aria-label="5 of 6 steps complete"><span /></div>
                <div className="gow-incident-meta">5 of 6 steps complete</div>
                <a className="gow-continue-action" href="/workspace/reports/2026-08-029">Continue Incident <Icon name="chevron" /></a>
              </div>
            </article>

            <article className="gow-panel">
              <PanelHeading icon="form" title="Recent Incidents" action={<a className="gow-panel-link" href="/workspace/reports">View All</a>} />
              <ul className="gow-list">
                {recentIncidents.map((incident) => (
                  <li className="gow-list-row" key={incident.number}>
                    <span className="gow-incident-number">{incident.number}</span>
                    <span className="gow-list-title">{incident.name}</span>
                    <StatusBadge tone={incident.tone === "warning" ? "warning" : incident.tone === "complete" ? "complete" : undefined}>{incident.state}</StatusBadge>
                    <span className="gow-list-time">{incident.time}</span>
                  </li>
                ))}
              </ul>
            </article>

            <article className="gow-panel">
              <PanelHeading icon="folder" title="Frequently Used Forms" action={<a className="gow-panel-link" href="/workspace/forms">View All</a>} />
              <ul className="gow-list">
                {frequentForms.map((form) => (
                  <li className="gow-form-row" key={form}>
                    <span className="gow-row-icon"><Icon name="form" /></span>
                    <span>{form}</span>
                    <Icon name="printer" />
                  </li>
                ))}
              </ul>
            </article>
          </section>

          <section className="gow-secondary-grid" aria-label="Daily work and activity">
            <article className="gow-panel">
              <PanelHeading icon="clipboard" title="Your Daily Checklist" action={<span className="gow-panel-link">3 items</span>} />
              <div className="gow-check-row"><span className="gow-check-control" /><span>Complete Assignment Roster</span><a className="gow-small-button" href="/workspace/admin/paperwork/roster">Open</a></div>
              <div className="gow-check-row"><span className="gow-check-control" /><span>Complete Uniform Inspection Log</span><a className="gow-small-button" href="/workspace/admin/paperwork/uniform">Open</a></div>
              <div className="gow-check-row"><span className="gow-check-control" /><span>Open Count Sheet</span><a className="gow-small-button" href="/workspace/count-sheet">Open</a></div>
            </article>

            <article className="gow-panel">
              <PanelHeading icon="link" title="Quick Links" />
              {[
                ["Forms Library", "form", "/workspace/forms"],
                ["Policy Expert", "shield", "/workspace/policy-expert"],
                ["My Account", "user", "/workspace/account"],
                ["Help & Support", "headset", "/workspace/help"],
              ].map(([label, icon, href]) => (
                <div className="gow-link-row" key={label}>
                  <a href={href}>
                    <span className="gow-row-icon"><Icon name={icon as IconName} /></span>
                    <span>{label}</span>
                    <Icon name="chevron" />
                  </a>
                </div>
              ))}
            </article>

            <article className="gow-panel">
              <PanelHeading icon="activity" title="Recent Activity" action={<a className="gow-panel-link" href="/workspace/activity">View All</a>} />
              {[
                ["Report 2026-08-029 updated", "18 min ago"],
                ["Policy question answered", "42 min ago"],
                ["Form viewed: 005/409", "1 hr ago"],
                ["Count sheet opened", "2 hr ago"],
                ["Logged in", "8:12 AM"],
              ].map(([label, time]) => (
                <div className="gow-activity-row" key={label}><span className="gow-activity-dot" /><span>{label}</span><span className="gow-list-time">{time}</span></div>
              ))}
            </article>
          </section>

          <footer className="gow-dashboard-footer">
            <div className="gow-quote"><span className="gow-quote-mark">“</span><span>Discipline is the bridge between goals and accomplishment.</span></div>
            <div className="gow-values" aria-label="Workplace values"><span><Icon name="shield" /> Security</span><span><Icon name="user" /> Service</span><span><Icon name="link" /> Teamwork</span></div>
            <div className="gow-date-time">Mon, Aug 18, 2026<br />8:42 AM</div>
          </footer>
        </div>
      </main>
    </div>
  );
}
