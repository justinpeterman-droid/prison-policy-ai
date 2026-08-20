import { FormEvent, useState } from "react";
import { StatusMessage } from "../../design-system/Primitives";

interface AdminElevationDialogProps {
  onSubmit: (pin: string) => Promise<void>;
  error?: string | null;
  busy?: boolean;
}

export function AdminElevationDialog({ onSubmit, error, busy = false }: AdminElevationDialogProps) {
  const [pin, setPin] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!pin.trim() || busy) return;
    await onSubmit(pin.trim());
  }

  return (
    <section className="admin-elevation" aria-labelledby="admin-confirm-title">
      <div className="admin-elevation-mark" aria-hidden="true">◆</div>
      <div className="admin-elevation-copy">
        <p className="admin-kicker">Protected workspace</p>
        <h1 id="admin-confirm-title">Administrator confirmation</h1>
        <p>Confirm your administrator PIN to enter the Operational Command Center. This elevation expires after inactivity.</p>
      </div>
      <form onSubmit={(event) => void submit(event)} className="admin-elevation-form">
        <label htmlFor="admin-pin">Administrator PIN</label>
        <input
          id="admin-pin"
          type="password"
          inputMode="text"
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
        <button className="admin-primary-button" type="submit" disabled={busy || !pin.trim()}>
          {busy ? "Confirming…" : "Enter Admin Center"}
        </button>
      </form>
      <p className="admin-security-note">Administrative access and saved changes are attributed to your individual account.</p>
    </section>
  );
}
