import { App } from "./App";
import { AuthProvider, useAuth } from "./features/auth/AuthProvider";
import { LoginPage } from "./features/auth/LoginPage";

function LoadingScreen() {
  return (
    <main className="login-page" aria-busy="true" aria-label="Checking sign-in">
      <section className="login-card">
        <div className="login-brand">
          <div className="login-shield" aria-hidden="true">✓</div>
          <div>
            <p className="login-brand-name">S.L.U.T</p>
            <p className="login-brand-line">Secure · Logical · Unified · Trusted</p>
          </div>
        </div>
        <div className="login-heading">
          <p className="login-overline">Guided Operations Workspace</p>
          <h1>Checking your session…</h1>
          <p>Connecting securely. No work is being changed.</p>
        </div>
      </section>
    </main>
  );
}

function SessionError() {
  const { message, refresh } = useAuth();
  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="session-error-title">
        <div className="login-heading">
          <p className="login-overline">Connection problem</p>
          <h1 id="session-error-title">The workspace could not be reached</h1>
          <p>{message ?? "Check the connection and try again."}</p>
        </div>
        <button className="login-submit" onClick={() => void refresh()} type="button">Try again</button>
      </section>
    </main>
  );
}

function AuthenticatedWorkspace() {
  const { status, profile } = useAuth();
  if (status === "loading") return <LoadingScreen />;
  if (status === "error") return <SessionError />;
  if (status !== "authenticated" || !profile) return <LoginPage />;
  if (profile.mustChangePin) {
    return (
      <main className="login-page">
        <section className="login-card">
          <div className="login-heading">
            <p className="login-overline">Account protection</p>
            <h1>Change your temporary PIN</h1>
            <p>A temporary PIN must be replaced before other workspace features can open.</p>
          </div>
        </section>
      </main>
    );
  }
  return <App profile={profile} />;
}

export function Root() {
  return (
    <AuthProvider>
      <AuthenticatedWorkspace />
    </AuthProvider>
  );
}
