import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  KeyRound,
  Laptop,
  LogOut,
  MonitorSmartphone,
  RefreshCw,
  ShieldCheck,
  Smartphone,
  Trash2,
  UserRound,
} from "lucide-react";
import { ApiError, apiRequest, designPreviewEnabled, requestId } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { Button, EmptyState, Notice, PageHeader, Section } from "../components/ui";
import { previewSessions } from "../data/preview";
import type { AccountSession } from "../types";

interface RawSession {
  session_id: string;
  device_label: string;
  persistent: boolean;
  created_at: string;
  last_used_at: string;
  renewal_expires_at: string;
  current: boolean;
}

function mapSession(raw: RawSession): AccountSession {
  return {
    sessionId: raw.session_id,
    deviceLabel: raw.device_label,
    persistent: raw.persistent,
    createdAt: raw.created_at,
    lastUsedAt: raw.last_used_at,
    renewalExpiresAt: raw.renewal_expires_at,
    current: raw.current,
  };
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function AccountPage() {
  const { profile, logout } = useAuth();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<AccountSession[]>(designPreviewEnabled ? previewSessions : []);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const loadSessions = async () => {
    if (designPreviewEnabled) return;
    setError(null);
    try {
      const result = await apiRequest<{ items: RawSession[] }>("/web-api/account/sessions");
      setSessions(result.items.map(mapSession));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Sessions could not be loaded.");
    }
  };

  useEffect(() => {
    void loadSessions();
  }, []);

  const revoke = async (session: AccountSession) => {
    setBusyId(session.sessionId);
    setError(null);
    try {
      if (!designPreviewEnabled) {
        await apiRequest<void>(`/web-api/account/sessions/${session.sessionId}`, {
          method: "DELETE",
          headers: { "Idempotency-Key": requestId("session") },
        });
      }
      setSessions((current) => current.filter((item) => item.sessionId !== session.sessionId));
      setNotice(`${session.deviceLabel} was signed out.`);
      if (session.current) {
        await logout();
        navigate("/sign-in", { replace: true });
      }
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The session was not revoked.");
    } finally {
      setBusyId(null);
    }
  };

  const signOutAll = async () => {
    setBusyId("all");
    setError(null);
    try {
      if (!designPreviewEnabled) {
        await apiRequest<void>("/web-api/account/logout-all", {
          method: "POST",
          headers: { "Idempotency-Key": requestId("logout_all") },
          body: JSON.stringify({}),
        });
      }
      await logout();
      navigate("/sign-in", { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Sessions could not be signed out.");
      setBusyId(null);
    }
  };

  return (
    <div className="page-stack account-page">
      <PageHeader
        eyebrow="Security and preferences"
        title="Account & sessions"
        description="Review your profile, change your PIN, and control every active device session."
      />

      {error ? <Notice tone="danger">{error}</Notice> : null}
      {notice ? <Notice tone="success">{notice}</Notice> : null}

      <div className="account-grid">
        <div className="account-main-stack">
          <Section title="Your profile" description="Identity and role are managed by an authorized administrator.">
            <div className="profile-card">
              <div className="profile-card__avatar"><UserRound aria-hidden="true" /></div>
              <div className="profile-card__identity">
                <h3>{profile?.displayName}</h3>
                <p>{profile?.rank ?? "Staff member"} · {profile?.shift ?? "Shift not assigned"}</p>
                <div className="profile-card__tags">
                  <span>{profile?.employeeNumber}</span>
                  <span>{profile?.role === "admin" ? "Administrator" : "Officer"}</span>
                  <span className="profile-active"><CheckCircle2 aria-hidden="true" /> Active</span>
                </div>
              </div>
            </div>
            <dl className="profile-details">
              <div><dt>Employee number</dt><dd>{profile?.employeeNumber}</dd></div>
              <div><dt>Role</dt><dd>{profile?.role === "admin" ? "Administrator" : "Officer"}</dd></div>
              <div><dt>Rank</dt><dd>{profile?.rank ?? "Not assigned"}</dd></div>
              <div><dt>Shift</dt><dd>{profile?.shift ?? "Not assigned"}</dd></div>
            </dl>
          </Section>

          <Section
            title="Active sessions"
            description="A session represents one signed-in browser or Access device."
            action={<Button variant="quiet" size="sm" onClick={() => void loadSessions()} icon={<RefreshCw aria-hidden="true" />}>Refresh</Button>}
          >
            {sessions.length ? (
              <div className="session-list">
                {sessions.map((session) => (
                  <article className="session-item" key={session.sessionId}>
                    <div className="session-item__icon">
                      {session.deviceLabel.toLowerCase().includes("phone") || session.deviceLabel.toLowerCase().includes("iphone") ? <Smartphone aria-hidden="true" /> : <Laptop aria-hidden="true" />}
                    </div>
                    <div className="session-item__copy">
                      <div><strong>{session.deviceLabel}</strong>{session.current ? <span>Current session</span> : null}</div>
                      <p>Last used {formatDateTime(session.lastUsedAt)} · {session.persistent ? "Remembered browser" : "Standard session"}</p>
                      <small>Session expires {formatDateTime(session.renewalExpiresAt)}</small>
                    </div>
                    <Button
                      variant={session.current ? "secondary" : "danger"}
                      size="sm"
                      onClick={() => void revoke(session)}
                      disabled={busyId === session.sessionId}
                      icon={session.current ? <LogOut aria-hidden="true" /> : <Trash2 aria-hidden="true" />}
                    >
                      {session.current ? "Sign out" : "Revoke"}
                    </Button>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState icon={<MonitorSmartphone aria-hidden="true" />} title="No active sessions" description="No device sessions were returned for this account." />
            )}
          </Section>
        </div>

        <aside className="account-side-stack">
          <Section title="PIN security">
            <div className="security-action">
              <span className="security-action__icon"><KeyRound aria-hidden="true" /></span>
              <div><strong>Change your PIN</strong><p>Updates the credential used by both the web and Access clients.</p></div>
              <Link className="button button--secondary button--sm" to="/change-pin">Change PIN</Link>
            </div>
          </Section>

          <Section title="Shared device guidance">
            <Notice tone="warning">
              <strong>Use a private browser when possible.</strong>
              <p>On a shared device, do not remember the browser. Sign out and close every window when finished.</p>
            </Notice>
          </Section>

          <Section title="Sign out everywhere">
            <div className="danger-zone">
              <AlertTriangle aria-hidden="true" />
              <p>This revokes every active session for your account, including Access and other browsers.</p>
              <Button variant="danger" onClick={() => void signOutAll()} disabled={busyId === "all"} icon={<ShieldCheck aria-hidden="true" />}>Sign out all sessions</Button>
            </div>
          </Section>
        </aside>
      </div>
    </div>
  );
}
