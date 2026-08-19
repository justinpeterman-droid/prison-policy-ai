import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import type { SessionProfile } from "../features/auth/api";
import "./officer-workspace-layout.css";

interface OfficerWorkspaceLayoutProps {
  profile: SessionProfile;
}

interface OfficerNavigationItem {
  label: string;
  to: string;
  icon: string;
  end?: boolean;
}

const NAVIGATION: readonly OfficerNavigationItem[] = [
  { label: "Home", to: "/", end: true, icon: "⌂" },
  { label: "New Report", to: "/new-report", icon: "+" },
  { label: "Reports", to: "/reports", icon: "▣" },
  { label: "Policy Expert", to: "/policy-expert", icon: "◇" },
  { label: "Forms Library", to: "/forms", icon: "▤" },
  { label: "Account", to: "/account", icon: "●" },
];

function initials(displayName: string): string {
  const pieces = displayName.trim().split(/\s+/).filter(Boolean);
  return pieces.slice(-2).map((piece) => piece[0]?.toUpperCase() ?? "").join("") || "U";
}

export function OfficerWorkspaceLayout({ profile }: OfficerWorkspaceLayoutProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const officerInitials = initials(profile.displayName);
  return (
    <div className="officer-shell">
      <aside className={menuOpen ? "officer-shell-sidebar open" : "officer-shell-sidebar"}>
        <div className="officer-shell-brand">
          <span className="officer-shell-shield" aria-hidden="true">✓</span>
          <div>
            <strong>S.L.U.T</strong>
            <span>Secure · Logical · Unified · Trusted</span>
          </div>
          <button
            type="button"
            className="officer-shell-close"
            aria-label="Close navigation menu"
            onClick={() => setMenuOpen(false)}
          >
            ×
          </button>
        </div>
        <nav className="officer-shell-nav" aria-label="Officer navigation">
          {NAVIGATION.map((item) => (
            <NavLink
              key={item.label}
              to={item.to}
              end={item.end}
              aria-label={item.label}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) => isActive ? "active" : undefined}
            >
              <span aria-hidden="true">{item.icon}</span>
              <strong>{item.label}</strong>
            </NavLink>
          ))}
        </nav>
        <div className="officer-shell-system" aria-label="System status">
          <span><i aria-hidden="true" /> System online</span>
          <small>Individual secure session</small>
        </div>
        <footer className="officer-shell-footer">
          <strong>S.L.U.T</strong>
          <span>Better tools. Safer facilities.</span>
        </footer>
      </aside>

      {menuOpen ? (
        <button
          type="button"
          className="officer-shell-scrim"
          aria-label="Close navigation menu"
          onClick={() => setMenuOpen(false)}
        />
      ) : null}

      <div className="officer-shell-main">
        <header className="officer-shell-topbar">
          <button
            type="button"
            className="officer-shell-menu"
            aria-label="Open navigation menu"
            onClick={() => setMenuOpen(true)}
          >
            ☰
          </button>
          <div className="officer-shell-status"><i aria-hidden="true" /> Online</div>
          <div className="officer-shell-user">
            <span>{officerInitials}</span>
            <div>
              <strong>{profile.displayName}</strong>
              <small>{profile.shift ? `${profile.shift} Shift` : "Shift not assigned"}</small>
            </div>
          </div>
        </header>
        <main className="officer-shell-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
