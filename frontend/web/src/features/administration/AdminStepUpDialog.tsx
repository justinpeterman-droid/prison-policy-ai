import { FormEvent, useState } from "react";
import { StatusMessage } from "../../design-system/Primitives";

interface AdminStepUpDialogProps {
  title: string;
  description: string;
  confirmLabel?: string;
  busy?: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: (pin: string) => Promise<void>;
}

export function AdminStepUpDialog({
  title,
  description,
  confirmLabel = "Confirm action",
  busy = false,
  error,
  onCancel,
  onConfirm,
}: AdminStepUpDialogProps) {
  const [pin, setPin] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!pin.trim() || busy) return;
    await onConfirm(pin.trim());
  }

  return (
    <div className="admin-modal-backdrop" role="presentation">
      <section className="admin-modal" role="dialog" aria-modal="true" aria-labelledby="admin-step-up-title">
        <div className="admin-modal-icon" aria-hidden="true">✓</div>
        <h2 id="admin-step-up-title">{title}</h2>
        <p>{description}</p>
        <form onSubmit={(event) => void submit(event)}>
          <label htmlFor="admin-step-up-pin">Administrator PIN</label>
          <input
            id="admin-step-up-pin"
            type="password"
            autoComplete="current-password"
            value={pin}
            onChange={(event) => setPin(event.target.value)}
            disabled={busy}
          />
          {error ? (
            <StatusMessage as="p" className="admin-form-error" tone="destructive" unstyled aria-atomic="true">
              {error}
            </StatusMessage>
          ) : null}
          <div className="admin-modal-actions">
            <button type="button" className="admin-secondary-button" onClick={onCancel} disabled={busy}>Cancel</button>
            <button type="submit" className="admin-primary-button" disabled={busy || !pin.trim()}>
              {busy ? "Confirming…" : confirmLabel}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
