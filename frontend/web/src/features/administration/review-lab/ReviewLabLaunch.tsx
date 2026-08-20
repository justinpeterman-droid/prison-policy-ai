import { useState } from "react";
import { issueReviewLabHandoff, requestAdminStepUp } from "../api";
import { AdminStepUpDialog } from "../AdminStepUpDialog";

export function ReviewLabLaunch() {
  const [showConfirm, setShowConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function launch(pin: string) {
    setBusy(true);
    setError(null);
    try {
      await requestAdminStepUp(pin, "review_lab_handoff");
      const handoff = await issueReviewLabHandoff();
      if (!handoff.url.startsWith("/access-handoff#")) throw new Error("Review Lab returned an unsafe destination.");
      window.location.assign(handoff.url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Review Lab could not be opened.");
      setBusy(false);
    }
  }

  return (
    <div className="admin-page admin-review-lab-page">
      <header className="admin-page-header"><div><p className="admin-kicker">Administration</p><h1>Review Lab</h1><p>Open the existing Review Lab with a short-lived, one-use browser handoff tied to your administrator account.</p></div></header>
      <section className="admin-review-lab-card">
        <div className="admin-review-lab-visual" aria-hidden="true"><span>◆</span><span>↗</span></div>
        <div><h2>Open protected review workspace</h2><p>Your main Guided Operations session stays here. Review Lab receives a separate, short-lived browser session; the handoff cannot be replayed.</p><ul><li>No PIN or bearer token is placed in a readable page field.</li><li>The launch is individually attributed and audited.</li><li>The handoff expires quickly if it is not used.</li></ul></div>
        <button className="admin-primary-button admin-launch-button" type="button" onClick={() => setShowConfirm(true)}>Open Review Lab <span aria-hidden="true">↗</span></button>
      </section>
      {showConfirm ? <AdminStepUpDialog title="Confirm Review Lab launch" description="Confirm your administrator PIN to create a one-use Review Lab handoff." confirmLabel="Open Review Lab" busy={busy} error={error} onCancel={() => { setShowConfirm(false); setError(null); }} onConfirm={launch} /> : null}
    </div>
  );
}
