import { FormEvent, useEffect, useState } from "react";
import type { AdminStaffMember } from "../api";
import { AdminStepUpDialog } from "../AdminStepUpDialog";
import { updateStaffProfile } from "./api";

interface StaffProfileEditorProps {
  staff: AdminStaffMember;
  onSaved: () => void;
}

export function StaffProfileEditor({ staff, onSaved }: StaffProfileEditorProps) {
  const [editing, setEditing] = useState(false);
  const [employeeNumber, setEmployeeNumber] = useState(staff.employeeNumber);
  const [rank, setRank] = useState(staff.rank ?? "");
  const [shift, setShift] = useState(staff.shift ?? "");
  const [active, setActive] = useState(staff.isActive);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEmployeeNumber(staff.employeeNumber);
    setRank(staff.rank ?? "");
    setShift(staff.shift ?? "");
    setActive(staff.isActive);
    setEditing(false);
    setConfirming(false);
    setError(null);
  }, [staff]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!employeeNumber.trim()) {
      setError("Employee number is required.");
      return;
    }
    setError(null);
    setConfirming(true);
  }

  async function confirm(pin: string) {
    setBusy(true);
    setError(null);
    try {
      await updateStaffProfile(staff.staffId, {
        employeeNumber: employeeNumber.trim(),
        rank: rank.trim() || null,
        shift: shift.trim() || null,
        isActive: active,
      }, pin);
      setConfirming(false);
      setEditing(false);
      onSaved();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Staff changes could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  if (!editing) {
    return (
      <button className="admin-text-button" type="button" onClick={() => setEditing(true)}>
        Edit staff profile
      </button>
    );
  }

  return (
    <>
      <form className="admin-staff-editor" onSubmit={submit}>
        <div className="admin-staff-editor-fields">
          <label>Employee number<input value={employeeNumber} onChange={(event) => setEmployeeNumber(event.target.value)} /></label>
          <label>Rank<input value={rank} onChange={(event) => setRank(event.target.value)} /></label>
          <label>Shift<input aria-label="Shift" value={shift} onChange={(event) => setShift(event.target.value)} /></label>
          <label className="admin-checkbox-field"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} /><span>Active staff member</span></label>
        </div>
        {error ? <p className="admin-form-error" role="alert">{error}</p> : null}
        <div className="admin-action-cluster">
          <button className="admin-secondary-button" type="button" onClick={() => setEditing(false)}>Cancel</button>
          <button className="admin-primary-button" type="submit">Save staff changes</button>
        </div>
      </form>
      {confirming ? (
        <AdminStepUpDialog
          title="Confirm staff changes"
          description={`Save corrections to ${staff.displayName}. The change is attributed to your administrator account.`}
          confirmLabel="Save staff changes"
          busy={busy}
          error={error}
          onCancel={() => { setConfirming(false); setError(null); }}
          onConfirm={confirm}
        />
      ) : null}
    </>
  );
}
