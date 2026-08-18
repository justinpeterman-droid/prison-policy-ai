import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, KeyRound, ShieldCheck } from "lucide-react";
import { ApiError } from "../api/client";
import { preventDefault, useAuth } from "../auth/AuthProvider";
import { Button, Notice } from "../components/ui";

export function ChangePinPage() {
  const { changePin, profile } = useAuth();
  const navigate = useNavigate();
  const [currentPin, setCurrentPin] = useState("");
  const [newPin, setNewPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    if (newPin !== confirmPin) {
      setError("The new PIN entries do not match.");
      return;
    }
    if (!/^[A-Za-z0-9]{4,8}$/.test(newPin)) {
      setError("Use 4–8 letters or numbers for the new PIN.");
      return;
    }
    setBusy(true);
    try {
      await changePin({ currentPin, newPin });
      navigate("/", { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The PIN could not be changed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="pin-page" id="main-content">
      <section className="pin-card">
        <div className="pin-card__mark" aria-hidden="true"><ShieldCheck /></div>
        <p className="eyebrow">Account security</p>
        <h1>{profile?.mustChangePin ? "Create a new PIN to continue" : "Change your PIN"}</h1>
        <p className="pin-card__intro">
          Your PIN protects both the Access and web clients. The new value takes effect for your account across the platform.
        </p>

        {error ? <Notice tone="danger">{error}</Notice> : null}

        <form className="pin-form" onSubmit={preventDefault(submit)}>
          <label className="field">
            <span>Current or temporary PIN</span>
            <input
              type="password"
              autoComplete="current-password"
              minLength={4}
              maxLength={8}
              value={currentPin}
              onChange={(event) => setCurrentPin(event.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>New PIN</span>
            <input
              type="password"
              autoComplete="new-password"
              minLength={4}
              maxLength={8}
              pattern="[A-Za-z0-9]{4,8}"
              value={newPin}
              onChange={(event) => setNewPin(event.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>Confirm new PIN</span>
            <input
              type="password"
              autoComplete="new-password"
              minLength={4}
              maxLength={8}
              pattern="[A-Za-z0-9]{4,8}"
              value={confirmPin}
              onChange={(event) => setConfirmPin(event.target.value)}
              required
            />
          </label>
          <Button type="submit" disabled={busy} icon={<ArrowRight aria-hidden="true" />}>
            {busy ? "Updating PIN…" : "Update PIN and continue"}
          </Button>
        </form>

        <div className="pin-rules">
          <KeyRound aria-hidden="true" />
          <div>
            <strong>PIN requirements</strong>
            <span>4–8 letters or numbers. Leading zeroes are preserved. Do not reuse a shared or easily guessed value.</span>
          </div>
        </div>
      </section>
    </main>
  );
}
