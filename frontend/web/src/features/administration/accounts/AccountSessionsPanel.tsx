import { useEffect, useState } from "react";
import { AdminStepUpDialog } from "../AdminStepUpDialog";
import { listAccountSessions, revokeAccountSession, type AdminAccountSession } from "./api";

interface AccountSessionsPanelProps {
  accountId: string;
}

function formatTime(value: string | null): string {
  if (!value) return "Unknown";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown" : date.toLocaleString();
}

export function AccountSessionsPanel({ accountId }: AccountSessionsPanelProps) {
  const [sessions, setSessions] = useState<AdminAccountSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<AdminAccountSession | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      setSessions(await listAccountSessions(accountId));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Account sessions could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
    // Account ID is the complete load key.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountId]);

  async function confirm(pin: string) {
    if (!pending) return;
    setBusy(true);
    setError(null);
    try {
      await revokeAccountSession(accountId, pending.sessionId, pin);
      setPending(null);
      await reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The session could not be revoked.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="admin-session-panel" aria-labelledby="admin-sessions-heading">
      <div className="admin-panel-heading">
        <div><p>Browser access</p><h3 id="admin-sessions-heading">Active Sessions</h3></div>
        <button className="admin-text-button" type="button" onClick={() => void reload()}>Refresh</button>
      </div>
      {loading ? <div className="admin-rail-state">Loading sessions…</div> : null}
      {error ? <div className="admin-rail-state error" role="alert">{error}</div> : null}
      {!loading && !error ? (
        <div className="admin-session-list">
          {sessions.filter((session) => !session.revokedAt).map((session) => (
            <article key={session.sessionId}>
              <span className="admin-session-device" aria-hidden="true">▣</span>
              <div>
                <strong>{session.deviceLabel}</strong>
                <small>{session.persistent ? "Persistent session" : "Session"} · Last used {formatTime(session.lastUsedAt)}</small>
                <small>Access expires {formatTime(session.accessExpiresAt)}</small>
              </div>
              <button className="admin-secondary-button" type="button" aria-label={`Revoke ${session.deviceLabel}`} onClick={() => setPending(session)}>Revoke</button>
            </article>
          ))}
          {!sessions.some((session) => !session.revokedAt) ? <div className="admin-empty-row">No active sessions.</div> : null}
        </div>
      ) : null}
      {pending ? (
        <AdminStepUpDialog
          title="Confirm session revocation"
          description={`Sign out ${pending.deviceLabel}. The employee will need to authenticate again on that browser.`}
          confirmLabel="Revoke session"
          busy={busy}
          error={error}
          onCancel={() => { setPending(null); setError(null); }}
          onConfirm={confirm}
        />
      ) : null}
    </section>
  );
}
