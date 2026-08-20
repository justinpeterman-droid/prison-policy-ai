import { ReactNode, useEffect, useState } from "react";
import { WebApiError } from "../../api/client";
import { enterAdminElevation, getAdminElevation, type AdminElevationState } from "./api";
import { AdminElevationDialog } from "./AdminElevationDialog";

interface AdminGateProps {
  children: ReactNode;
}

export function AdminGate({ children }: AdminGateProps) {
  const [state, setState] = useState<AdminElevationState | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void getAdminElevation()
      .then((value) => {
        if (active) setState(value);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setState({ elevated: false, elevationExpiresAt: null });
        setError(reason instanceof Error ? reason.message : "Administrator status could not be checked.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!state?.elevated || !state.elevationExpiresAt) return;
    const expires = Date.parse(state.elevationExpiresAt);
    if (!Number.isFinite(expires)) return;
    const delay = Math.max(0, expires - Date.now());
    const timer = window.setTimeout(() => {
      setState({ elevated: false, elevationExpiresAt: null });
    }, Math.min(delay + 50, 2_147_483_647));
    return () => window.clearTimeout(timer);
  }, [state]);

  async function confirm(pin: string) {
    setBusy(true);
    setError(null);
    try {
      const value = await enterAdminElevation(pin);
      setState(value);
    } catch (reason) {
      const message = reason instanceof WebApiError
        ? reason.message
        : reason instanceof Error
          ? reason.message
          : "Administrator confirmation failed.";
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <section className="admin-loading" aria-busy="true" aria-label="Checking administrator access">
        <span className="admin-loading-orbit" aria-hidden="true" />
        <strong>Checking administrator access…</strong>
      </section>
    );
  }

  if (!state?.elevated) {
    return <AdminElevationDialog onSubmit={confirm} error={error} busy={busy} />;
  }

  return <>{children}</>;
}
