import { useState } from "react";

interface TemporaryPinDialogProps {
  temporaryPin: string;
  expiresAt: string | null;
  onClose: () => void;
}

export function TemporaryPinDialog({ temporaryPin, expiresAt, onClose }: TemporaryPinDialogProps) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(temporaryPin);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="admin-modal-backdrop" role="presentation">
      <section className="admin-modal admin-pin-modal" role="dialog" aria-modal="true" aria-labelledby="temporary-pin-title">
        <div className="admin-modal-icon gold" aria-hidden="true">1×</div>
        <h2 id="temporary-pin-title">Temporary PIN</h2>
        <p>This value is shown once. Give it to the employee through your approved channel. It will be removed from this page when you close the dialog.</p>
        <div className="admin-temporary-pin" aria-label="Temporary PIN">{temporaryPin}</div>
        {expiresAt ? <p className="admin-pin-expiry">Expires {new Date(expiresAt).toLocaleString()}</p> : null}
        <div className="admin-modal-actions">
          <button type="button" className="admin-secondary-button" onClick={() => void copy()}>{copied ? "Copied" : "Copy PIN"}</button>
          <button type="button" className="admin-primary-button" onClick={onClose}>Close and clear</button>
        </div>
      </section>
    </div>
  );
}
