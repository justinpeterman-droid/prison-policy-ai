import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import type { SessionProfile } from "../auth/api";
import { AccountsStaffPage } from "./accounts/AccountsStaffPage";
import { AuditLogPage } from "./audit/AuditLogPage";
import { SystemHealthPage } from "./health/SystemHealthPage";
import { AdminIncidentWorkspace } from "./incidents/AdminIncidentWorkspace";
import { AdminIncidentsPage } from "./incidents/AdminIncidentsPage";
import { AdminOverviewPage } from "./overview/AdminOverviewPage";
import { PaperworkCenterPage } from "./paperwork/PaperworkCenterPage";
import { ReviewLabLaunch } from "./review-lab/ReviewLabLaunch";
import "./admin.css";
import "./admin-entry.css";

interface AdminLayoutProps {
  profile: SessionProfile;
}

const adminNavigation = [
  ["Overview", "/admin/overview", "⌂"],
  ["All Incidents", "/admin/incidents", "▤"],
  ["Paperwork Center", "/admin/paperwork", "▦"],
  ["Accounts & Staff", "/admin/accounts-staff", "♙"],
  ["Audit Log", "/admin/audit", "◫"],
  ["System Health", "/admin/health", "◇"],
  ["Review Lab", "/admin/review-lab", "↗"],
] as const;

export function AdminLayout({ profile }: AdminLayoutProps) {
  return (
    <div className="admin-shell">
      <div className="admin-context-bar">
        <div><span className="admin-context-gem" aria-hidden="true">◆</span><strong>Administrator workspace</strong><span>{profile.displayName}</span></div>
        <span>Elevated access · individually attributed</span>
      </div>
      <div className="admin-layout-grid">
        <aside className="admin-subnav">
          <div className="admin-subnav-heading"><small>Operational</small><strong>Command Center</strong></div>
          <nav aria-label="Administration navigation">
            {adminNavigation.map(([label, to, icon]) => (
              <NavLink key={to} to={to} className={({ isActive }) => isActive ? "is-active" : ""}>
                <span aria-hidden="true">{icon}</span><span>{label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="admin-subnav-foot"><span aria-hidden="true">✓</span><p><strong>Protected mode</strong><small>Sensitive actions require fresh PIN confirmation.</small></p></div>
        </aside>
        <div className="admin-content">
          <Routes>
            <Route index element={<Navigate to="overview" replace />} />
            <Route path="overview" element={<AdminOverviewPage />} />
            <Route path="incidents" element={<AdminIncidentsPage />} />
            <Route path="incidents/:incidentId" element={<AdminIncidentWorkspace />} />
            <Route path="paperwork" element={<PaperworkCenterPage />} />
            <Route path="accounts-staff" element={<AccountsStaffPage />} />
            <Route path="audit" element={<AuditLogPage />} />
            <Route path="health" element={<SystemHealthPage />} />
            <Route path="review-lab" element={<ReviewLabLaunch />} />
            <Route path="*" element={<Navigate to="overview" replace />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}
