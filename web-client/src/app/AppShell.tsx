import { useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Bell,
  BookOpenText,
  Bookmark,
  ChevronDown,
  ClipboardList,
  FilePlus2,
  Gauge,
  Home,
  Landmark,
  LogOut,
  Menu,
  MessageSquareText,
  Search,
  Settings,
  ShieldCheck,
  UserRoundCog,
  X,
} from "lucide-react";
import { useAuth } from "../auth/AuthProvider";

interface NavItem {
  to: string;
  label: string;
  icon: typeof Home;
  end?: boolean;
}

const officerItems: NavItem[] = [
  { to: "/", label: "Dashboard", icon: Home, end: true },
  { to: "/policy", label: "Policy Expert", icon: MessageSquareText },
  { to: "/reports/new", label: "New report", icon: FilePlus2 },
  { to: "/reports", label: "My reports", icon: ClipboardList },
  { to: "/library", label: "Policy library", icon: BookOpenText },
  { to: "/saved", label: "Saved", icon: Bookmark },
];

const accountItems: NavItem[] = [
  { to: "/account", label: "Account & sessions", icon: Settings },
];

const adminItems: NavItem[] = [
  { to: "/admin", label: "Admin overview", icon: Gauge, end: true },
  { to: "/admin/staff", label: "Staff & accounts", icon: UserRoundCog },
  { to: "/admin/reports", label: "All reports", icon: Landmark },
  { to: "/admin/audit", label: "Audit activity", icon: ShieldCheck },
  { to: "/admin/health", label: "System health", icon: Gauge },
];

const pageTitles: Array<[RegExp, string]> = [
  [/^\/$/, "Dashboard"],
  [/^\/policy/, "Policy Expert"],
  [/^\/reports\/new/, "New incident report"],
  [/^\/reports\//, "Report workspace"],
  [/^\/reports/, "My reports"],
  [/^\/library/, "Policy library"],
  [/^\/saved/, "Saved workspace"],
  [/^\/account/, "Account & sessions"],
  [/^\/admin\/staff/, "Staff & accounts"],
  [/^\/admin\/reports/, "All reports"],
  [/^\/admin\/audit/, "Audit activity"],
  [/^\/admin\/health/, "System health"],
  [/^\/admin/, "Admin overview"],
];

function NavigationGroup({
  label,
  items,
  onNavigate,
}: {
  label?: string;
  items: NavItem[];
  onNavigate?(): void;
}) {
  return (
    <div className="nav-group">
      {label ? <p className="nav-group__label">{label}</p> : null}
      <nav aria-label={label ?? "Primary"}>
        {items.map(({ to, label: itemLabel, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) => `nav-link${isActive ? " nav-link--active" : ""}`}
          >
            <Icon aria-hidden="true" />
            <span>{itemLabel}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

function Brand() {
  return (
    <NavLink className="brand" to="/" aria-label="Standard Logistics and Unit Tools home">
      <span className="brand__mark" aria-hidden="true">
        <img
          src="/static/shield-crystal-front.png"
          alt=""
          onError={(event) => {
            event.currentTarget.hidden = true;
          }}
        />
        <ShieldCheck />
      </span>
      <span className="brand__text">
        <strong>
          <span>S</span>tandard <span>L</span>ogistics
        </strong>
        <small>
          &amp; <span>U</span>nit <span>T</span>ools
        </small>
      </span>
    </NavLink>
  );
}

function UserSummary({ compact = false }: { compact?: boolean }) {
  const { profile, logout } = useAuth();
  const navigate = useNavigate();
  const initials = (profile?.displayName ?? "Staff member")
    .split(" ")
    .filter(Boolean)
    .slice(-2)
    .map((part) => part[0])
    .join("");

  const signOut = async () => {
    await logout();
    navigate("/sign-in", { replace: true });
  };

  return (
    <div className={`user-summary${compact ? " user-summary--compact" : ""}`}>
      <span className="avatar" aria-hidden="true">{initials}</span>
      <div className="user-summary__copy">
        <strong>{profile?.displayName ?? "Staff member"}</strong>
        <span>{profile?.role === "admin" ? "Administrator" : profile?.shift ?? "Officer"}</span>
      </div>
      <button className="icon-button icon-button--inverse" onClick={signOut} aria-label="Sign out">
        <LogOut aria-hidden="true" />
      </button>
    </div>
  );
}

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { profile, isDesignPreview } = useAuth();
  const title = useMemo(
    () => pageTitles.find(([pattern]) => pattern.test(location.pathname))?.[1] ?? "Workspace",
    [location.pathname],
  );

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Application navigation">
        <Brand />
        <div className="sidebar__body">
          <NavigationGroup items={officerItems} />
          {profile?.role === "admin" ? <NavigationGroup label="Administration" items={adminItems} /> : null}
          <NavigationGroup label="Your account" items={accountItems} />
        </div>
        <div className="sidebar__footer">
          <div className="connection-status">
            <span className="connection-status__dot" aria-hidden="true" />
            <span>Secure connection</span>
          </div>
          <UserSummary />
        </div>
      </aside>

      <div className="app-shell__main">
        <header className="topbar">
          <div className="topbar__start">
            <button
              className="icon-button topbar__menu"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
            >
              <Menu aria-hidden="true" />
            </button>
            <div>
              <p className="topbar__kicker">Standard Logistics &amp; Unit Tools</p>
              <strong className="topbar__title">{title}</strong>
            </div>
          </div>
          <div className="topbar__actions">
            {isDesignPreview ? <span className="preview-badge">Design preview</span> : null}
            <button
              className="topbar-search"
              aria-label="Search reports"
              onClick={() => navigate("/reports")}
            >
              <Search aria-hidden="true" />
              <span>Search reports</span>
            </button>
            <button className="icon-button" aria-label="Notifications">
              <Bell aria-hidden="true" />
              <span className="notification-dot" aria-hidden="true" />
            </button>
            <button
              className="topbar-profile"
              onClick={() => setProfileOpen((open) => !open)}
              aria-expanded={profileOpen}
              aria-label="Open profile menu"
            >
              <span className="avatar avatar--small" aria-hidden="true">
                {(profile?.displayName ?? "Staff").split(" ").at(-1)?.[0] ?? "S"}
              </span>
              <ChevronDown aria-hidden="true" />
            </button>
          </div>
          {profileOpen ? (
            <div className="profile-popover">
              <UserSummary compact />
            </div>
          ) : null}
        </header>

        <main id="main-content" className="content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>

      {mobileOpen ? (
        <div className="mobile-nav-layer">
          <button
            className="mobile-nav-layer__backdrop"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="mobile-nav" aria-label="Mobile navigation">
            <div className="mobile-nav__header">
              <Brand />
              <button className="icon-button icon-button--inverse" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
                <X aria-hidden="true" />
              </button>
            </div>
            <div className="mobile-nav__body">
              <NavigationGroup items={officerItems} onNavigate={() => setMobileOpen(false)} />
              {profile?.role === "admin" ? (
                <NavigationGroup label="Administration" items={adminItems} onNavigate={() => setMobileOpen(false)} />
              ) : null}
              <NavigationGroup label="Your account" items={accountItems} onNavigate={() => setMobileOpen(false)} />
            </div>
            <UserSummary />
          </aside>
        </div>
      ) : null}

      <nav className="mobile-bottom-nav" aria-label="Quick navigation">
        {officerItems.slice(0, 4).map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? "active" : "")}>
            <Icon aria-hidden="true" />
            <span>{label.replace("My ", "")}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
