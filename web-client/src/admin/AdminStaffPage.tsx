import { useMemo, useState } from "react";
import {
  BadgeCheck,
  Circle,
  Filter,
  KeyRound,
  MoreHorizontal,
  Search,
  ShieldCheck,
  UserPlus,
  X,
} from "lucide-react";
import { designPreviewEnabled } from "../api/client";
import { Button, Notice, PageHeader, Section } from "../components/ui";
import { AdminAdapterPending, previewStaff } from "./shared";

export function AdminStaffPage() {
  const [query, setQuery] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const filtered = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!value) return previewStaff;
    return previewStaff.filter((person) => [person.employee, person.name, person.rank, person.shift, person.status].some((item) => item.toLowerCase().includes(value)));
  }, [query]);

  if (!designPreviewEnabled) {
    return (
      <AdminAdapterPending
        title="Staff & accounts"
        description="Create and manage accounts only for approved staff identities."
      />
    );
  }

  return (
    <div className="page-stack admin-page">
      <PageHeader
        eyebrow="Identity administration"
        title="Staff & accounts"
        description="Create and manage accounts only for approved staff identities. Temporary PINs are one-time values."
        actions={<Button onClick={() => setShowCreate(true)} icon={<UserPlus aria-hidden="true" />}>Create account</Button>}
      />

      <Section className="admin-table-section">
        <div className="report-toolbar">
          <label className="search-field"><Search aria-hidden="true" /><span className="sr-only">Search staff</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search employee number, name, rank, or shift" /></label>
          <Button variant="secondary" icon={<Filter aria-hidden="true" />}>Filters</Button>
        </div>
        <div className="data-table-wrap">
          <table className="data-table staff-table">
            <thead><tr><th>Staff member</th><th>Assignment</th><th>Account role</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead>
            <tbody>
              {filtered.map((person) => (
                <tr key={person.employee}>
                  <td><strong className="cell-title">{person.name}</strong><span className="cell-subtitle">{person.employee}</span></td>
                  <td><strong className="cell-title">{person.rank}</strong><span className="cell-subtitle">{person.shift}</span></td>
                  <td><span className="role-badge">{person.role === "admin" ? <ShieldCheck aria-hidden="true" /> : <BadgeCheck aria-hidden="true" />}{person.role === "admin" ? "Administrator" : person.status === "No account" ? "Not assigned" : "Officer"}</span></td>
                  <td><span className={`account-status account-status--${person.status.toLowerCase().replace(" ", "-")}`}><Circle aria-hidden="true" />{person.status}</span></td>
                  <td><button className="icon-button" aria-label={`Manage ${person.name}`}><MoreHorizontal aria-hidden="true" /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      {showCreate ? (
        <div className="modal-layer" role="presentation">
          <button className="modal-layer__backdrop" aria-label="Close dialog" onClick={() => setShowCreate(false)} />
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="create-account-title">
            <div className="modal__header"><div><p className="eyebrow">Step-up protected</p><h2 id="create-account-title">Create staff account</h2></div><button className="icon-button" onClick={() => setShowCreate(false)} aria-label="Close"><X aria-hidden="true" /></button></div>
            <Notice tone="warning"><strong>Administrator PIN confirmation required.</strong><p>The server will confirm the exact purpose before creating the account.</p></Notice>
            <form className="modal-form" onSubmit={(event) => { event.preventDefault(); setShowCreate(false); }}>
              <label className="field"><span>Approved staff member</span><select required defaultValue=""><option value="" disabled>Select from roster</option><option>F-1121 · Sgt. Morgan Quinn</option></select></label>
              <label className="field"><span>Account role</span><select defaultValue="officer"><option value="officer">Officer</option><option value="admin">Administrator</option></select></label>
              <label className="field"><span>Administrator PIN</span><input type="password" autoComplete="current-password" minLength={4} maxLength={8} required /></label>
              <div className="modal__actions"><Button variant="secondary" type="button" onClick={() => setShowCreate(false)}>Cancel</Button><Button type="submit" icon={<KeyRound aria-hidden="true" />}>Confirm and create</Button></div>
            </form>
          </section>
        </div>
      ) : null}
    </div>
  );
}
