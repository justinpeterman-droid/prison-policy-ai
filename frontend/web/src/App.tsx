import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { AccountPage } from "./features/account/AccountPage";
import { signOutCurrentBrowserSession } from "./features/account/api";
import { AdminGate } from "./features/administration/AdminGate";
import { AdminLayout } from "./features/administration/AdminLayout";
import type { SessionProfile } from "./features/auth/api";
import { OfficerHomePage } from "./features/dashboard/OfficerHomePage";
import { FormsLibraryPage } from "./features/forms-library/FormsLibraryPage";
import { DocumentStudioPage } from "./features/incidents/DocumentStudioPage";
import { NewReportPage } from "./features/incidents/NewReportPage";
import { ReportsPage } from "./features/incidents/ReportsPage";
import { CountSheetPage } from "./features/paperwork/count-sheet/CountSheetPage";
import { PolicyExpertPage } from "./features/policy/PolicyExpertPage";
import sidebarMountains from "./assets/sidebar-mountains-v3.webp";
import "./guided-operations.css";
import "./incident-workspace.css";

interface AppProps {
  profile: SessionProfile;
  onAuthenticationChanged?: () => void;
}

type NavIcon = "home" | "plus" | "folder" | "shield" | "form" | "user" | "admin";
type UtilityIcon = "menu" | "close" | "chevron" | "check" | "admin";

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
  if (name === "admin") return <svg {...common}><path d="M12 3 5 6v5c0 4.8 2.8 8.2 7 10 4.2-1.8 7-5.2 7-10V6z"/><path d="M8.5 13.5h7M10 10.5h4"/></svg>;
  return <svg {...common}><circle cx="12" cy="8" r="4"/><path d="M4.5 21c.8-4.2 3.2-6 7.5-6s6.7 1.8 7.5 6"/></svg>;
}

function UtilityIcon({ name }: { name: UtilityIcon }) {
  const common = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  if (name === "menu") return <svg {...common}><path d="M4 7h16M4 12h16M4 17h16" /></svg>;
  if (name === "close") return <svg {...common}><path d="m6 6 12 12M18 6 6 18" /></svg>;
  if (name === "check") return <svg {...common}><path d="m5 12 4 4L19 6" /></svg>;
  if (name === "admin") return <svg {...common}><path d="M12 3 5 6v5c0 4.8 2.8 8.2 7 10 4.2-1.8 7-5.2 7-10V6z" /><path d="M9 12h6" /></svg>;
  return <svg {...common}><path d="m8 10 4 4 4-4" /></svg>;
}

function BrandShield() {
  return <span className="gow-shield" aria-hidden="true"><Icon name="shield" /></span>;
}

function NotFoundPage() {
  return (
    <section className="iw-page" aria-labelledby="not-found-heading">
      <header className="iw-page-header">
        <div>
          <p className="iw-eyebrow">Guided Operations Workspace</p>
          <h1 id="not-found-heading">Workspace page not found</h1>
          <p>Use the officer navigation to return to an available workspace.</p>
        </div>
      </header>
      <div className="iw-empty-state">
        <div className="iw-empty-icon" aria-hidden="true">◇</div>
        <h2>The requested workspace is not available</h2>
        <p>No incident, form, account, or paperwork information was changed.</p>
      </div>
    </section>
  );
}

export function App({ profile, onAuthenticationChanged }: AppProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [signOutPending, setSignOutPending] = useState(false);
  const [profileMenuError, setProfileMenuError] = useState<string | null>(null);
  const [online, setOnline] = useState(() => navigator.onLine);
  const menuTriggerRef = useRef<HTMLButtonElement>(null);
  const menuCloseRef = useRef<HTMLButtonElement>(null);
  const profileTriggerRef = useRef<HTMLButtonElement>(null);
  const profileMenuRef = useRef<HTMLDivElement>(null);
  const initials = profileInitials(profile.displayName);

  useEffect(() => {
    const updateConnectivity = () => setOnline(navigator.onLine);
    window.addEventListener("online", updateConnectivity);
    window.addEventListener("offline", updateConnectivity);
    return () => {
      window.removeEventListener("online", updateConnectivity);
      window.removeEventListener("offline", updateConnectivity);
    };
  }, []);

  const closeMobileMenu = (restoreFocus = true) => {
    setMenuOpen(false);
    if (restoreFocus) menuTriggerRef.current?.focus();
  };

  useEffect(() => {
    if (!menuOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    menuCloseRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeMobileMenu();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  useEffect(() => {
    if (!profileMenuOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setProfileMenuOpen(false);
        profileTriggerRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [profileMenuOpen]);

  const closeProfileMenu = (restoreFocus = false) => {
    setProfileMenuOpen(false);
    if (restoreFocus) profileTriggerRef.current?.focus();
  };

  const focusProfileMenuItem = (position: "first" | "last") => {
    const items = profileMenuRef.current?.querySelectorAll<HTMLElement>("[role='menuitem']:not([disabled])");
    if (!items?.length) return;
    items[position === "first" ? 0 : items.length - 1]?.focus();
  };

  const handleProfileMenuKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    const items = Array.from(profileMenuRef.current?.querySelectorAll<HTMLElement>("[role='menuitem']:not([disabled])") ?? []);
    if (!items.length) return;
    const current = items.indexOf(document.activeElement as HTMLElement);
    let next = current;
    if (event.key === "ArrowDown") next = current < items.length - 1 ? current + 1 : 0;
    else if (event.key === "ArrowUp") next = current > 0 ? current - 1 : items.length - 1;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = items.length - 1;
    else return;
    event.preventDefault();
    items[next]?.focus();
  };

  const signOut = async () => {
    setSignOutPending(true);
    setProfileMenuError(null);
    try {
      await signOutCurrentBrowserSession();
      closeProfileMenu();
      onAuthenticationChanged?.();
    } catch (reason: unknown) {
      setProfileMenuError(reason instanceof Error ? reason.message : "This device could not be signed out.");
    } finally {
      setSignOutPending(false);
    }
  };

  return (
    <div className="gow-app">
      <aside className={`gow-sidebar ${menuOpen ? "is-open" : ""}`} aria-label="Primary navigation">
        <div className="gow-brand">
          <BrandShield />
          <div>
            <p className="gow-brand-name">S.L.U.T</p>
            <p className="gow-brand-subtitle">Secure · Logical · Unified · Trusted</p>
          </div>
          <button ref={menuCloseRef} className="gow-mobile-menu-button" type="button" aria-label="Close navigation menu" title="Close navigation menu" onClick={() => closeMobileMenu()}><UtilityIcon name="close" /></button>
        </div>

        <nav className="gow-nav" aria-label="Officer navigation">
          {navigation.map((item) => (
            <NavLink key={item.label} className="gow-nav-link" to={item.to} end={item.end} aria-label={item.label} onClick={() => closeMobileMenu(false)}>
              <span className="gow-nav-icon"><Icon name={item.icon} /></span>
              <span className="gow-nav-label">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {profile.role === "admin" ? (
          <div className="gow-admin-entry">
            <span className="gow-admin-entry-label">ADMINISTRATION</span>
            <NavLink className="gow-nav-link gow-admin-link" to="/admin/overview" aria-label="Administration" onClick={() => closeMobileMenu(false)}>
              <span className="gow-nav-icon"><Icon name="admin" /></span>
              <span className="gow-nav-label">Administration</span>
            </NavLink>
          </div>
        ) : null}

        <img className="gow-sidebar-mountain-scene" src={sidebarMountains} alt="" aria-hidden="true" width="252" height="540" loading="lazy" decoding="async" fetchPriority="low" />
        <div className="gow-sidebar-footer"><strong>S.L.U.T</strong><p>Better tools. Safer facilities.</p></div>
      </aside>

      {menuOpen ? <button className="gow-mobile-scrim" type="button" aria-label="Close navigation" onClick={() => closeMobileMenu()} /> : null}

      <main className="gow-workspace">
        <header className="gow-topbar" aria-label="Workspace status">
          <button ref={menuTriggerRef} className="gow-mobile-menu-trigger" type="button" aria-label="Open navigation menu" title="Open navigation menu" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}><UtilityIcon name="menu" /></button>
          <div className="gow-status-chip" role="status" aria-live="polite"><span className={`gow-online-dot${online ? "" : " is-offline"}`} /><span>{online ? "Online" : "Offline"}</span></div>
          <div className="gow-status-chip"><UtilityIcon name="check" /><span>Secure browser session</span></div>
          {profile.role === "admin" ? <div className="gow-status-chip gow-admin-context-chip"><UtilityIcon name="admin" /><span>Administrator</span></div> : null}
          <div className="gow-profile-menu">
            <button ref={profileTriggerRef} className="gow-user-chip" type="button" aria-label={profile.displayName} aria-expanded={profileMenuOpen} aria-haspopup="menu" aria-controls="gow-profile-menu" onClick={() => setProfileMenuOpen((open) => !open)} onKeyDown={(event) => {
              if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault();
                setProfileMenuOpen(true);
                requestAnimationFrame(() => focusProfileMenuItem(event.key === "ArrowDown" ? "first" : "last"));
              }
            }}>
              <span className="gow-avatar">{initials}</span><span>{profile.displayName}</span><UtilityIcon name="chevron" />
            </button>
            {profileMenuOpen ? (
              <div ref={profileMenuRef} id="gow-profile-menu" className="gow-profile-popover" role="menu" aria-label="Profile and session" onKeyDown={handleProfileMenuKeyDown}>
                <div className="gow-profile-context"><strong>{profile.role === "admin" ? "Administrator" : "Officer"}</strong><span>{profile.shift ? `${profile.shift} Shift` : "Shift not assigned"}</span><span>Secure browser session</span></div>
                <NavLink role="menuitem" to="/account" onClick={() => closeProfileMenu()}>Account and session</NavLink>
                <button className="gow-profile-sign-out" role="menuitem" type="button" disabled={signOutPending} onClick={() => void signOut()}>{signOutPending ? "Signing out…" : "Sign out this device"}</button>
                {profileMenuError ? <p className="gow-profile-error" role="alert">{profileMenuError}</p> : null}
              </div>
            ) : null}
          </div>
        </header>

        <Routes>
          <Route path="/" element={<OfficerHomePage profile={profile} />} />
          <Route path="/new-report" element={<NewReportPage profile={profile} />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/reports/:incidentId" element={<DocumentStudioPage />} />
          <Route path="/policy-expert" element={<PolicyExpertPage />} />
          <Route path="/forms" element={<FormsLibraryPage />} />
          <Route path="/account" element={<AccountPage profile={profile} onAuthenticationChanged={onAuthenticationChanged} />} />
          <Route path="/count-sheet" element={<CountSheetPage profile={profile} />} />
          <Route
            path="/admin/*"
            element={profile.role === "admin" ? (
              <AdminGate><AdminLayout profile={profile} /></AdminGate>
            ) : <NotFoundPage />}
          />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  );
}
