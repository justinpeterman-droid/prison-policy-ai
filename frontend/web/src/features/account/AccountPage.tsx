import { useCallback, useEffect, useState } from "react";
import { StatusMessage } from "../../design-system/Primitives";
import type { SessionProfile } from "../auth/api";
import { ChangePinForm } from "./ChangePinForm";
import {
  fetchAccountSessions,
  logoutAllAccountSessions,
  revokeAccountSession,
  signOutCurrentBrowserSession,
  type AccountSession,
} from "./api";
import "./account.css";

interface AccountPageProps {
  profile: SessionProfile;
  onAuthenticationChanged?: () => void;
}

function formatTime(value: string | null): string {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AccountPage({
  profile,
  onAuthenticationChanged,
}: AccountPageProps) {
  const [sessions, setSessions] = useState<AccountSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busySessionId, setBusySessionId] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setSessionError(null);
    void fetchAccountSessions()
      .then((items) => {
        if (!active) return;
        setSessions(items.map((item) => ({
          ...item,
          current: item.current || item.sessionId === profile.sessionId,
        })));
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setSessions([]);
        setSessionError(
          reason instanceof Error
            ? reason.message
            : "Active sessions could not be loaded.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [profile.sessionId, reloadToken]);

  const revoke = useCallback(async (session: AccountSession) => {
    setBusySessionId(session.sessionId);
    setActionError(null);
    try {
      await revokeAccountSession(session.sessionId);
      setSessions((current) => current.filter((item) => item.sessionId !== session.sessionId));
    } catch (reason: unknown) {
      setActionError(
        reason instanceof Error ? reason.message : "The session could not be signed out.",
      );
    } finally {
      setBusySessionId(null);
    }
  }, []);

  const signOutCurrent = useCallback(async () => {
    setBusySessionId(profile.sessionId);
    setActionError(null);
    try {
      await signOutCurrentBrowserSession();
      onAuthenticationChanged?.();
    } catch (reason: unknown) {
      setActionError(
        reason instanceof Error ? reason.message : "This device could not be signed out.",
      );
    } finally {
      setBusySessionId(null);
    }
  }, [onAuthenticationChanged, profile.sessionId]);

  const signOutEverywhere = useCallback(async () => {
    setBusySessionId("all");
    setActionError(null);
    try {
      await logoutAllAccountSessions();
      setSessions([]);
      onAuthenticationChanged?.();
    } catch (reason: unknown) {
      setActionError(
        reason instanceof Error ? reason.message : "Sessions could not be signed out.",
      );
    } finally {
      setBusySessionId(null);
    }
  }, [onAuthenticationChanged]);

  return (
    <section className="account-page" aria-labelledby="account-heading">
      <header className="account-heading">
        <div>
          <p>Officer Utilities</p>
          <h1 id="account-heading">My Account</h1>
          <span>Manage your PIN and individual browser sessions.</span>
        </div>
      </header>

      <div className="account-grid">
        <section className="account-panel" aria-label="Employee identity">
          <header>
            <p>Read-only profile</p>
            <h2>Employee identity</h2>
          </header>
          <dl className="account-identity-list">
            <div><dt>Name</dt><dd>{profile.displayName}</dd></div>
            <div><dt>Employee number</dt><dd>{profile.employeeNumber}</dd></div>
            <div><dt>Rank</dt><dd>{profile.rank ?? "Not assigned"}</dd></div>
            <div><dt>Shift</dt><dd>{profile.shift ?? "Not assigned"}</dd></div>
            <div><dt>Role</dt><dd>{profile.role === "admin" ? "Administrator" : "Officer"}</dd></div>
          </dl>
          <p className="account-note">
            Staff-record corrections are made by an authorized administrator.
          </p>
        </section>

        <section className="account-panel">
          <header>
            <p>Account protection</p>
            <h2>Change PIN</h2>
          </header>
          <ChangePinForm onChanged={onAuthenticationChanged} />
        </section>
      </div>

      <section className="account-panel sessions-panel" aria-labelledby="sessions-heading">
        <header>
          <div>
            <p>Security</p>
            <h2 id="sessions-heading">Active browser sessions</h2>
          </div>
          <div className="account-session-actions">
            <button
              type="button"
              onClick={() => void signOutCurrent()}
              disabled={busySessionId !== null}
            >
              Sign out this device
            </button>
            <button
              type="button"
              className="danger"
              onClick={() => void signOutEverywhere()}
              disabled={busySessionId !== null}
            >
              Sign out everywhere
            </button>
          </div>
        </header>

        {actionError ? (
          <StatusMessage as="p" className="account-form-message error" tone="destructive" unstyled aria-atomic="true">
            {actionError}
          </StatusMessage>
        ) : null}
        {loading ? <div className="account-state" aria-busy="true">Loading active sessions…</div> : null}
        {sessionError ? (
          <StatusMessage className="account-state error" tone="dependency-unavailable" unstyled aria-atomic="true">
            <span>{sessionError}</span>
            <button type="button" onClick={() => setReloadToken((value) => value + 1)}>
              Try sessions again
            </button>
          </StatusMessage>
        ) : null}
        {!loading && !sessionError && sessions.length === 0 ? (
          <div className="account-state">No active sessions are available.</div>
        ) : null}
        {sessions.length > 0 ? (
          <div className="account-session-list">
            {sessions.map((session) => (
              <article className="account-session-card" aria-label={session.deviceLabel} key={session.sessionId}>
                <div>
                  <div className="account-session-title">
                    <strong>{session.deviceLabel}</strong>
                    {session.current ? <span>Current session</span> : null}
                  </div>
                  <dl>
                    <div><dt>Last active</dt><dd>{formatTime(session.lastSeenAt)}</dd></div>
                    <div><dt>Started</dt><dd>{formatTime(session.createdAt)}</dd></div>
                    <div><dt>Expires</dt><dd>{formatTime(session.expiresAt)}</dd></div>
                  </dl>
                </div>
                {!session.current ? (
                  <button
                    type="button"
                    onClick={() => void revoke(session)}
                    disabled={busySessionId !== null}
                    aria-label={`Sign out ${session.deviceLabel}`}
                  >
                    {busySessionId === session.sessionId ? "Signing out…" : "Sign out"}
                  </button>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </section>
  );
}
