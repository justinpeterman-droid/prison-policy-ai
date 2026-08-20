import { FormEvent, useEffect, useMemo, useState } from "react";
import { listAdminStaff, type AdminStaffMember } from "../api";
import {
  createAccount,
  createStaff,
  resetAccountPin,
  revokeAccountSessions,
  unlockAccount,
  updateAccount,
} from "../mutations";
import { AdminStepUpDialog } from "../AdminStepUpDialog";
import { AccountSessionsPanel } from "./AccountSessionsPanel";
import { StaffProfileEditor } from "./StaffProfileEditor";
import { TemporaryPinDialog } from "./TemporaryPinDialog";

interface PendingAction {
  title: string;
  description: string;
  confirmLabel: string;
  run: (pin: string) => Promise<void>;
}

export function AccountsStaffPage() {
  const [items, setItems] = useState<AdminStaffMember[]>([]);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [temporaryPin, setTemporaryPin] = useState<{ pin: string; expiresAt: string | null } | null>(null);
  const [showNewStaff, setShowNewStaff] = useState(false);
  const [newStaff, setNewStaff] = useState({ employeeNumber: "", rank: "", firstName: "", lastName: "", shift: "" });

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void listAdminStaff(submittedQuery)
      .then((page) => {
        if (!active) return;
        setItems(page.items);
        setSelectedId((current) => current && page.items.some((item) => item.staffId === current)
          ? current
          : page.items[0]?.staffId ?? null);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Staff records could not be loaded.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [reload, submittedQuery]);

  const selected = useMemo(
    () => items.find((item) => item.staffId === selectedId) ?? null,
    [items, selectedId],
  );

  function search(event: FormEvent) {
    event.preventDefault();
    setSubmittedQuery(query.trim());
  }

  async function confirmAction(pin: string) {
    if (!pending) return;
    setActionBusy(true);
    setActionError(null);
    try {
      await pending.run(pin);
      setPending(null);
      setReload((value) => value + 1);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "The administrator action could not be completed.");
    } finally {
      setActionBusy(false);
    }
  }

  function queueCreateAccount() {
    if (!selected || selected.account) return;
    setPending({
      title: "Create employee account",
      description: `Create an individual user account for ${selected.displayName}. A temporary PIN will be shown once after confirmation.`,
      confirmLabel: "Create account",
      run: async (pin) => {
        const result = await createAccount(selected.staffId, "user", pin);
        setTemporaryPin({ pin: result.temporary_pin, expiresAt: result.temporary_pin_expires_at });
      },
    });
  }

  function queueResetPin() {
    if (!selected?.account) return;
    setPending({
      title: "Reset temporary PIN",
      description: `Reset ${selected.displayName}’s PIN. Existing sessions may be affected and the new temporary PIN will be shown once.`,
      confirmLabel: "Reset PIN",
      run: async (pin) => {
        const result = await resetAccountPin(selected.account!.accountId, pin);
        setTemporaryPin({ pin: result.temporary_pin, expiresAt: result.temporary_pin_expires_at });
      },
    });
  }

  function queueAccountChange(nextRole: "user" | "admin", nextStatus: string) {
    if (!selected?.account) return;
    setPending({
      title: "Change account access",
      description: `Change ${selected.displayName} to ${nextRole} / ${nextStatus}. Last-active-administrator protection remains enforced by the server.`,
      confirmLabel: "Apply change",
      run: async (pin) => { await updateAccount(selected.account!.accountId, nextRole, nextStatus, pin); },
    });
  }

  function queueUnlock() {
    if (!selected?.account) return;
    setPending({
      title: "Unlock account",
      description: `Clear the current lock for ${selected.displayName}.`,
      confirmLabel: "Unlock account",
      run: async (pin) => { await unlockAccount(selected.account!.accountId, pin); },
    });
  }

  function queueRevokeSessions() {
    if (!selected?.account) return;
    setPending({
      title: "Sign out all employee sessions",
      description: `Revoke all active sessions for ${selected.displayName}. The employee will need to sign in again.`,
      confirmLabel: "Revoke sessions",
      run: async (pin) => { await revokeAccountSessions(selected.account!.accountId, pin); },
    });
  }

  function queueNewStaff(event: FormEvent) {
    event.preventDefault();
    if (!newStaff.employeeNumber.trim() || !newStaff.firstName.trim() || !newStaff.lastName.trim()) return;
    const draft = { ...newStaff };
    setPending({
      title: "Add staff member",
      description: `Create the staff profile for ${draft.firstName.trim()} ${draft.lastName.trim()}. This creates the roster identity only; an individual account is a separate action.`,
      confirmLabel: "Add staff member",
      run: async (pin) => {
        await createStaff({
          employeeNumber: draft.employeeNumber.trim(),
          rank: draft.rank.trim() || null,
          firstName: draft.firstName.trim(),
          lastName: draft.lastName.trim(),
          shift: draft.shift.trim() || null,
        }, pin);
        setShowNewStaff(false);
        setNewStaff({ employeeNumber: "", rank: "", firstName: "", lastName: "", shift: "" });
      },
    });
  }

  return (
    <div className="admin-page">
      <header className="admin-page-header">
        <div><p className="admin-kicker">Administration</p><h1>Accounts &amp; Staff</h1><p>Manage stable employee identities separately from individual sign-in accounts.</p></div>
        <button className="admin-primary-button" type="button" onClick={() => setShowNewStaff(true)}>Add staff member</button>
      </header>

      {showNewStaff ? (
        <form className="admin-new-staff-panel" onSubmit={queueNewStaff}>
          <div className="admin-panel-heading"><div><p>Roster identity</p><h2>New staff member</h2></div><button type="button" className="admin-text-button" onClick={() => setShowNewStaff(false)}>Close</button></div>
          <div className="admin-form-grid">
            <label>Employee number<input value={newStaff.employeeNumber} onChange={(e) => setNewStaff({ ...newStaff, employeeNumber: e.target.value })} /></label>
            <label>Rank<input value={newStaff.rank} onChange={(e) => setNewStaff({ ...newStaff, rank: e.target.value })} /></label>
            <label>First name<input value={newStaff.firstName} onChange={(e) => setNewStaff({ ...newStaff, firstName: e.target.value })} /></label>
            <label>Last name<input value={newStaff.lastName} onChange={(e) => setNewStaff({ ...newStaff, lastName: e.target.value })} /></label>
            <label>Shift<input value={newStaff.shift} onChange={(e) => setNewStaff({ ...newStaff, shift: e.target.value })} /></label>
          </div>
          <button className="admin-primary-button" type="submit">Continue with PIN confirmation</button>
        </form>
      ) : null}

      <div className="admin-split-workspace">
        <aside className="admin-staff-rail" aria-label="Staff list">
          <form className="admin-rail-search" onSubmit={search}>
            <label htmlFor="admin-staff-search">Search staff</label>
            <div><input id="admin-staff-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name or employee #" /><button type="submit" aria-label="Search staff">⌕</button></div>
          </form>
          {loading ? <div className="admin-rail-state">Loading staff…</div> : null}
          {error ? <div className="admin-rail-state error" role="alert">{error}</div> : null}
          {!loading && !error ? (
            <div className="admin-staff-list">
              {items.map((staff) => (
                <button key={staff.staffId} className={staff.staffId === selectedId ? "is-selected" : ""} type="button" onClick={() => setSelectedId(staff.staffId)}>
                  <span className="admin-staff-avatar" aria-hidden="true">{staff.displayName.split(/\s+/).slice(-2).map((part) => part[0]).join("")}</span>
                  <span><strong>{staff.displayName}</strong><small>{staff.employeeNumber} · {staff.shift ? `${staff.shift} Shift` : "No shift"}</small></span>
                  <em>{staff.isActive ? "Active" : "Inactive"}</em>
                </button>
              ))}
              {!items.length ? <div className="admin-rail-state">No matching staff.</div> : null}
            </div>
          ) : null}
        </aside>

        <section className="admin-staff-detail" aria-live="polite">
          {selected ? (
            <>
              <div className="admin-detail-hero">
                <div className="admin-detail-avatar" aria-hidden="true">{selected.displayName.split(/\s+/).slice(-2).map((part) => part[0]).join("")}</div>
                <div><p>Staff profile</p><h2>{selected.displayName}</h2><span>{selected.employeeNumber} · {selected.rank ?? "Rank not set"} · {selected.shift ? `${selected.shift} Shift` : "Shift not set"}</span></div>
                <span className={`admin-status-mark ${selected.isActive ? "operational" : "unavailable"}`}>{selected.isActive ? "Active staff" : "Inactive staff"}</span>
              </div>

              <div className="admin-staff-profile-actions">
                <StaffProfileEditor staff={selected} onSaved={() => setReload((value) => value + 1)} />
              </div>

              <section className="admin-account-card" aria-labelledby="linked-account-heading">
                <div className="admin-panel-heading"><div><p>Individual sign-in</p><h3 id="linked-account-heading">Linked Account</h3></div></div>
                {selected.account ? (
                  <>
                    <dl className="admin-account-facts">
                      <div><dt>Role</dt><dd>{selected.account.role === "admin" ? "Administrator" : "Officer"}</dd></div>
                      <div><dt>Status</dt><dd>{selected.account.status}</dd></div>
                      <div><dt>PIN state</dt><dd>{selected.account.mustChangePin ? "Temporary PIN" : "Set by employee"}</dd></div>
                    </dl>
                    <div className="admin-action-cluster">
                      <button className="admin-secondary-button" type="button" onClick={queueResetPin}>Reset PIN</button>
                      {selected.account.status === "locked" ? <button className="admin-secondary-button" type="button" onClick={queueUnlock}>Unlock</button> : null}
                      <button className="admin-secondary-button" type="button" onClick={queueRevokeSessions}>Revoke all sessions</button>
                      <button className="admin-secondary-button" type="button" onClick={() => queueAccountChange(selected.account!.role === "admin" ? "user" : "admin", selected.account!.status)}>{selected.account.role === "admin" ? "Change to officer" : "Make administrator"}</button>
                      <button className="admin-danger-button" type="button" onClick={() => queueAccountChange(selected.account!.role, selected.account!.status === "deactivated" ? "active" : "deactivated")}>{selected.account.status === "deactivated" ? "Reactivate" : "Deactivate"}</button>
                    </div>
                    <AccountSessionsPanel accountId={selected.account.accountId} />
                  </>
                ) : (
                  <div className="admin-account-empty"><div aria-hidden="true">◇</div><strong>No individual account</strong><p>This staff identity can appear on rosters without having web access.</p><button className="admin-primary-button" type="button" onClick={queueCreateAccount}>Create individual account</button></div>
                )}
              </section>
            </>
          ) : <div className="admin-empty-row">Select a staff member to view account controls.</div>}
        </section>
      </div>

      {pending ? <AdminStepUpDialog title={pending.title} description={pending.description} confirmLabel={pending.confirmLabel} busy={actionBusy} error={actionError} onCancel={() => { setPending(null); setActionError(null); }} onConfirm={confirmAction} /> : null}
      {temporaryPin ? <TemporaryPinDialog temporaryPin={temporaryPin.pin} expiresAt={temporaryPin.expiresAt} onClose={() => setTemporaryPin(null)} /> : null}
    </div>
  );
}
