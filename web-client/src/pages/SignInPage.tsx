import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Check,
  Eye,
  EyeOff,
  FileCheck2,
  LockKeyhole,
  MessageSquareText,
  ShieldCheck,
} from "lucide-react";
import { ApiError } from "../api/client";
import { preventDefault, useAuth } from "../auth/AuthProvider";
import { Button, Notice } from "../components/ui";

export function SignInPage() {
  const { login, isDesignPreview, previewAs } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [employeeNumber, setEmployeeNumber] = useState("");
  const [pin, setPin] = useState("");
  const [persistent, setPersistent] = useState(false);
  const [showPin, setShowPin] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await login({ employeeNumber: employeeNumber.trim(), pin, persistent });
      const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
      navigate(from && from !== "/sign-in" ? from : "/", { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Sign-in could not be completed.");
    } finally {
      setBusy(false);
    }
  };

  const preview = (role: "officer" | "admin") => {
    previewAs(role);
    navigate(role === "admin" ? "/admin" : "/", { replace: true });
  };

  return (
    <main className="auth-page" id="main-content">
      <section className="auth-brand-panel" aria-label="Product introduction">
        <div className="auth-brand-panel__inner">
          <div className="auth-brand">
            <span className="auth-brand__mark" aria-hidden="true">
              <img
                src="/static/shield-crystal-front.png"
                alt=""
                onError={(event) => {
                  event.currentTarget.hidden = true;
                }}
              />
              <ShieldCheck />
            </span>
            <div>
              <p>Standard Logistics &amp; Unit Tools</p>
              <strong>Policy guidance and report workspace</strong>
            </div>
          </div>

          <div className="auth-intro">
            <p className="eyebrow eyebrow--light">Secure staff access</p>
            <h1>One account. The same work, wherever you serve.</h1>
            <p>
              Use the same employee account as the Access client to continue reports, ask policy
              questions, and manage your work from a supported browser.
            </p>
          </div>

          <ul className="auth-benefits">
            <li>
              <MessageSquareText aria-hidden="true" />
              <span><strong>Cited policy answers</strong><small>Review the source passage beside every grounded answer.</small></span>
            </li>
            <li>
              <FileCheck2 aria-hidden="true" />
              <span><strong>Cross-client report continuity</strong><small>Resume the same report and revision from Access or the web.</small></span>
            </li>
            <li>
              <LockKeyhole aria-hidden="true" />
              <span><strong>Individual accountability</strong><small>Every save, export, and administrative action is attributable.</small></span>
            </li>
          </ul>

          <div className="auth-trust-note">
            <Check aria-hidden="true" />
            <span>AI helps organize documented facts. It does not invent facts or file anything for you.</span>
          </div>
        </div>
      </section>

      <section className="auth-form-panel" aria-label="Sign in">
        <div className="auth-form-wrap">
          <header className="auth-form-header">
            <p className="eyebrow">Authorized personnel</p>
            <h2>Sign in to your workspace</h2>
            <p>Enter the employee number and PIN issued to your account.</p>
          </header>

          {error ? <Notice tone="danger">{error}</Notice> : null}

          <form className="auth-form" onSubmit={preventDefault(submit)}>
            <label className="field">
              <span>Employee number</span>
              <input
                autoComplete="username"
                inputMode="text"
                value={employeeNumber}
                onChange={(event) => setEmployeeNumber(event.target.value)}
                placeholder="Enter employee number"
                required
                autoFocus
              />
            </label>

            <label className="field">
              <span>PIN</span>
              <span className="input-with-action">
                <input
                  type={showPin ? "text" : "password"}
                  autoComplete="current-password"
                  value={pin}
                  onChange={(event) => setPin(event.target.value)}
                  minLength={4}
                  maxLength={8}
                  pattern="[A-Za-z0-9]{4,8}"
                  placeholder="4–8 letters or numbers"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPin((visible) => !visible)}
                  aria-label={showPin ? "Hide PIN" : "Show PIN"}
                >
                  {showPin ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
                </button>
              </span>
            </label>

            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={persistent}
                onChange={(event) => setPersistent(event.target.checked)}
              />
              <span>
                <strong>Remember this browser</strong>
                <small>Do not select this on a shared or public device.</small>
              </span>
            </label>

            <Button type="submit" disabled={busy} icon={<ArrowRight aria-hidden="true" />}>
              {busy ? "Signing in…" : "Sign in securely"}
            </Button>
          </form>

          <div className="auth-help">
            <p>Account locked, PIN expired, or signing in for the first time?</p>
            <span>Contact an authorized administrator. Public self-registration is not available.</span>
          </div>

          {isDesignPreview ? (
            <div className="preview-switcher" aria-label="Design preview roles">
              <span>Preview the interface</span>
              <div>
                <Button variant="secondary" size="sm" onClick={() => preview("officer")}>Officer view</Button>
                <Button variant="secondary" size="sm" onClick={() => preview("admin")}>Admin view</Button>
              </div>
            </div>
          ) : null}

          {import.meta.env.VITE_SHOW_LEGACY_LINK === "true" ? (
            <a className="legacy-link" href="/login">Use legacy pilot access</a>
          ) : null}
        </div>
      </section>
    </main>
  );
}
