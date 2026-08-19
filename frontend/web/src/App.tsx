import { useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import type { SessionProfile } from "./features/auth/api";
import { HomePage } from "./features/dashboard/HomePage";
import { DocumentStudioPage } from "./features/incidents/DocumentStudioPage";
import { NewReportPage } from "./features/incidents/NewReportPage";
import { ReportsPage } from "./features/incidents/ReportsPage";
import { CountSheetPage } from "./features/paperwork/count-sheet/CountSheetPage";
import "./guided-operations.css";
import "./incident-workspace.css";

interface AppProps {
  profile: SessionProfile;
}

type NavIcon = "home" | "plus" | "folder" | "shield" | "form" | "user";

const navigation: Array<{ label: string; to: string; icon: NavIcon; end?: boolean }> = [
  { label: "Home", to: "/", icon: "home", end: true },
  { label: "New Report", to: "/new-report", icon: "plus" },
  { label: "Reports", to: "/reports", icon: "folder" },
  { label: "Policy Expert", to: "/policy-expert", icon: "shield" },
  { label: "Forms Library", to: "/forms", icon: "form" },
  { label: "Account", to: "/account", icon: "user" },
];

function profileInitials(displayName: string): string {
  const parts = displayName.trim().split(/\s+/).filter(Boolean);
  return parts.slice(-2).map((part) => part[0]?.toUpperCase() ?? "").join("") || "U";
}

function Icon({ name }: { name: NavIcon }) {
  const common = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  if (name === "home") return <svg {...common}><path d="m3 11 9-8 9 8"/><path d="M5.5 9.5V21h13V9.5"/><path d="M9.5 21v-7h5v7"/></svg>;
  if (name === "plus") return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/></svg>;
  if (name === "folder") return <svg {...common}><path d="M3 6.5h6l2 2h10v10.5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 10h18"/></svg>;
  if (name === "shield") return <svg {...common}><path d="M12 3 5 6v5c0 4.8 2.8 8.2 7 10 4.2-1.8 7-5.2 7-10V6z"/><path d="m9.2 12.2 1.8 1.8 3.9-4"/></svg>;
  if (name === "form") return <svg {...common}><path d="M6 3h9l4 4v14H6z"/><path d="M15 3v5h5M9 12h7M9 16h7"/></svg>;
  return <svg {...common}><circle cx="12" cy="8" r="4"/><path d="M4.5 21c.8-4.2 3.2-6 7.5-6s6.7 1.8 7.5 6"/></svg>;
}

function BrandShield() {
  return <span className="gow-shield" aria-hidden="true"><Icon name="shield" /></span>;
}

function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <section className="iw-page" aria-labelledby="placeholder-heading">
      <header className="iw-page-header">
        <div>
          <p className="iw-eyebrow">Guided Operations Workspace</p>
          <h1 id="placeholder-heading">{title}</h1>
          <p>{description}</p>
        </div>
      </header>
      <div className="iw-empty-state">
        <div className="iw-empty-icon" aria-hidden="true">◇</div>
        <h2>This workspace is scheduled in the next product milestone</h2>
        <p>The incident workflow is available now. This officer utility remains isolated until its own secure service and test gate are complete.</p>
      </div>
    </section>
  );
}

export function App({ profile }: AppProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const initials = profileInitials(profile.displayName);

  return (
    <div className="gow-app">
      <aside className={`gow-sidebar ${menuOpen ? "is-open" : ""}`}>
        <div className="gow-brand">
          <BrandShield />
          <div>
            <p className="gow-brand-name">S.L.U.T</p>
            <p className="gow-brand-subtitle">Secure · Logical · Unified · Trusted</p>
          </div>
          <button
            className="gow-mobile-menu-button"
            type="button"
            aria-label="Close navigation menu"
            onClick={() => setMenuOpen(false)}
          >
            ×
          </button>
        </div>

        <nav className="gow-nav" aria-label="Officer navigation">
          {navigation.map((item) => (
            <NavLink
              key={item.label}
              className="gow-nav-link"
              to={item.to}
              end={item.end}
              aria-label={item.label}
              onClick={() => setMenuOpen(false)}
            >
              <span className="gow-nav-icon"><Icon name={item.icon} /></span>
              <span className="gow-nav-label">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="gow-sidebar-status" aria-label="System status">
          <div className="gow-side-status-line"><span className="gow-side-dot" /> <strong>System Online</strong></div>
          <div className="gow-side-status-line"><span aria-hidden="true">✓</span> All systems operational</div>
          <div className="gow-side-help"><span aria-hidden="true">◉</span> Need Help?</div>
        </div>
        <div className="gow-sidebar-footer"><strong>S.L.U.T</strong><p>Better tools. Safer facilities.</p></div>
      </aside>

      {menuOpen ? <button className="gow-mobile-scrim" type="button" aria-label="Close navigation" onClick={() => setMenuOpen(false)} /> : null}

      <main className="gow-workspace">
        <header className="gow-topbar" aria-label="Workspace status">
          <button className="gow-mobile-menu-trigger" type="button" aria-label="Open navigation menu" onClick={() => setMenuOpen(true)}>☰</button>
          <div className="gow-status-chip"><span className="gow-online-dot" /><span>Online</span></div>
          <div className="gow-status-chip"><span aria-hidden="true">☁</span><span>Last synced 2 minutes ago</span></div>
          <div className="gow-status-chip"><span aria-hidden="true">✓</span><span>All changes saved</span></div>
          <div className="gow-notification" aria-label="2 notifications"><span aria-hidden="true">♢</span><span className="gow-notification-badge">2</span></div>
          <div className="gow-user-chip"><span className="gow-avatar">{initials}</span><span>{profile.displayName}</span><span aria-hidden="true">⌄</span></div>
        </header>

        <Routes>
          <Route path="/" element={<HomePage profile={profile} />} />
          <Route path="/new-report" element={<NewReportPage profile={profile} />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/reports/:incidentId" element={<DocumentStudioPage />} />
          <Route path="/policy-expert" element={<PlaceholderPage title="Policy Expert" description="Ask policy questions and receive citation-backed answers." />} />
          <Route path="/forms" element={<PlaceholderPage title="Forms Library" description="Browse and print approved operational forms." />} />
          <Route path="/account" element={<PlaceholderPage title="Account" description="Manage your PIN and active browser sessions." />} />
          <Route path="/count-sheet" element={<CountSheetPage profile={profile} />} />
          <Route path="*" element={<PlaceholderPage title="Workspace page not found" description="Use the officer navigation to return to an available workspace." />} />
        </Routes>
      </main>
    </div>
  );
}
