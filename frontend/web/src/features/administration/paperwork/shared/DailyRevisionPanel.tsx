import { useState } from "react";
import { StatusMessage } from "../../../../design-system/Primitives";
import {
  fetchDailyRevisions,
  restoreDailyRevision,
  type DailyRecord,
  type DailyRevision,
} from "../api";

interface DailyRevisionPanelProps {
  record: DailyRecord;
  onRestored: (record: DailyRecord) => void;
}

export function DailyRevisionPanel({ record, onRestored }: DailyRevisionPanelProps) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<DailyRevision[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [selected, setSelected] = useState<number | null>(null);

  async function toggle() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (items.length) return;
    setError(null);
    setLoading(true);
    setAnnouncement("Loading revision history.");
    try {
      const revisions = await fetchDailyRevisions(record.kind, record.recordId);
      setItems(revisions);
      setAnnouncement(revisions.length === 1 ? "1 revision loaded." : `${revisions.length} revisions loaded.`);
    } catch (reason) {
      setAnnouncement("");
      setError(reason instanceof Error ? reason.message : "Revision history could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  async function restore() {
    if (selected === null) return;
    setError(null);
    try {
      const restored = await restoreDailyRevision(record.kind, record.recordId, selected);
      setSelected(null);
      setItems([]);
      onRestored(restored);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The revision could not be restored.");
    }
  }

  return (
    <section className="daily-revision-panel">
      <button type="button" className="admin-secondary-button" onClick={() => void toggle()}>
        Revision history
      </button>
      <div className="gow-visually-hidden" role="status" aria-live="polite" aria-atomic="true">
        {announcement}
      </div>
      {open ? (
        <div>
          <h2>Revision history</h2>
          {loading ? <p>Loading revisions…</p> : null}
          {error ? (
            <StatusMessage className="admin-alert error" tone="destructive" aria-atomic="true">
              {error}
            </StatusMessage>
          ) : null}
          <ol>
            {items.map((item) => (
              <li key={item.revisionNumber}>
                <div>
                  <strong>Revision {item.revisionNumber}</strong>
                  <span>{new Date(item.createdAt).toLocaleString()} · editor {item.editorStaffMemberId}</span>
                  <small>{item.reason} · {item.changedFields.length ? item.changedFields.join(", ") : "initial record"}</small>
                </div>
                {item.revisionNumber !== record.revision ? (
                  <button type="button" onClick={() => setSelected(item.revisionNumber)} aria-label={`Restore revision ${item.revisionNumber}`}>
                    Restore
                  </button>
                ) : <em>Current</em>}
              </li>
            ))}
          </ol>
        </div>
      ) : null}
      {selected !== null ? (
        <div className="admin-dialog-backdrop">
          <section role="dialog" aria-modal="true" aria-label={`Restore revision ${selected}`} className="admin-confirm-dialog">
            <h2>Restore revision {selected}</h2>
            <p>This preserves current history and creates a new attributed revision from the selected content.</p>
            <div>
              <button type="button" className="admin-secondary-button" onClick={() => setSelected(null)}>Cancel</button>
              <button type="button" className="admin-primary-button" onClick={() => void restore()}>Confirm restore</button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
