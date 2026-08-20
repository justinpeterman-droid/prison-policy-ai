import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, StatusMessage } from "../../design-system/Primitives";
import { changePin } from "./api";

const PIN_MISMATCH_MESSAGE = "The new PIN values do not match.";

interface ChangePinFormProps {
  onChanged?: () => void;
  submitLabel?: string;
}

export function ChangePinForm({
  onChanged,
  submitLabel = "Change PIN",
}: ChangePinFormProps) {
  const [currentPin, setCurrentPin] = useState("");
  const [newPin, setNewPin] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    if (newPin !== confirmation) {
      setError(PIN_MISMATCH_MESSAGE);
      return;
    }
    setSubmitting(true);
    try {
      await changePin(currentPin, newPin);
      setCurrentPin("");
      setNewPin("");
      setConfirmation("");
      setSuccess("PIN changed. Sign in again with your new PIN when prompted.");
      onChanged?.();
    } catch (reason: unknown) {
      setError(
        reason instanceof Error
          ? reason.message
          : "The PIN could not be changed. Your entries are still visible.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const confirmationMismatch = error === PIN_MISMATCH_MESSAGE;

  return (
    <form className="account-pin-form" onSubmit={submit}>
      <div className="account-field-grid">
        <Field label="Current PIN" required>
          <input
            aria-label="Current PIN"
            type="password"
            inputMode="text"
            autoComplete="current-password"
            minLength={4}
            maxLength={8}
            pattern="[A-Za-z0-9]{4,8}"
            required
            value={currentPin}
            onChange={(event) => setCurrentPin(event.currentTarget.value)}
          />
        </Field>
        <Field label="New PIN" required>
          <input
            aria-label="New PIN"
            type="password"
            inputMode="text"
            autoComplete="new-password"
            minLength={4}
            maxLength={8}
            pattern="[A-Za-z0-9]{4,8}"
            required
            value={newPin}
            onChange={(event) => setNewPin(event.currentTarget.value)}
          />
        </Field>
        <Field label="Confirm new PIN" required>
          <input
            aria-label="Confirm new PIN"
            type="password"
            inputMode="text"
            autoComplete="new-password"
            minLength={4}
            maxLength={8}
            pattern="[A-Za-z0-9]{4,8}"
            required
            aria-invalid={confirmationMismatch || undefined}
            aria-errormessage={confirmationMismatch ? "account-pin-error" : undefined}
            value={confirmation}
            onChange={(event) => setConfirmation(event.currentTarget.value)}
          />
        </Field>
      </div>
      <p className="account-pin-guidance">
        Use 4 through 8 letters or numbers. Do not reuse the current PIN.
      </p>
      {error ? <StatusMessage as="p" id="account-pin-error" className="account-form-message error" tone="destructive">{error}</StatusMessage> : null}
      {success ? <StatusMessage as="p" className="account-form-message success" tone="success">{success}</StatusMessage> : null}
      <Button className="account-primary-button" variant="primary" type="submit" loading={submitting}>
        {submitting ? "Changing…" : submitLabel}
      </Button>
    </form>
  );
}
