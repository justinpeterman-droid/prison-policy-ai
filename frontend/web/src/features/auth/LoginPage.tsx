import { useState, type FormEvent } from "react";
import { StatusMessage } from "../../design-system/Primitives";
import { useAuth } from "./AuthProvider";
import "./login.css";

export function LoginPage() {
  const { message, signIn } = useAuth();
  const [employeeNumber, setEmployeeNumber] = useState("");
  const [pin, setPin] = useState("");
  const [persistent, setPersistent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!employeeNumber.trim() || !pin) return;
    setSubmitting(true);
    try {
      await signIn({ employeeNumber: employeeNumber.trim(), pin, persistent });
      setPin("");
    } catch {
      // The provider exposes the approved safe message above the form.
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-backdrop" aria-hidden="true" />
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-brand">
          <div className="login-shield" aria-hidden="true">✓</div>
          <div>
            <p className="login-brand-name">S.L.U.T</p>
            <p className="login-brand-line">Secure · Logical · Unified · Trusted</p>
          </div>
        </div>

        <div className="login-heading">
          <p className="login-overline">Guided Operations Workspace</p>
          <h1 id="login-title">Sign in to continue</h1>
          <p>Use your employee number and individual PIN.</p>
        </div>

        {message ? (
          <StatusMessage className="login-error" tone="destructive" unstyled aria-atomic="true">
            {message}
          </StatusMessage>
        ) : null}

        <form className="login-form" onSubmit={submit}>
          <label>
            <span>Employee number</span>
            <input
              autoComplete="username"
              inputMode="text"
              maxLength={64}
              onChange={(event) => setEmployeeNumber(event.target.value)}
              required
              type="text"
              value={employeeNumber}
            />
          </label>
          <label>
            <span>PIN</span>
            <input
              autoComplete="current-password"
              maxLength={8}
              minLength={4}
              onChange={(event) => setPin(event.target.value)}
              pattern="[A-Za-z0-9]{4,8}"
              required
              type="password"
              value={pin}
            />
          </label>
          <label className="login-remember">
            <input
              checked={persistent}
              onChange={(event) => setPersistent(event.target.checked)}
              type="checkbox"
            />
            <span>Keep me signed in on this device</span>
          </label>
          <button className="login-submit" disabled={submitting} type="submit">
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <footer className="login-footer">
          <strong>Authorized personnel only</strong>
          <span>Your session and activity are protected and attributable.</span>
        </footer>
      </section>
    </main>
  );
}
