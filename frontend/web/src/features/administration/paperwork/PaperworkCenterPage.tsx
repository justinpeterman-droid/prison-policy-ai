import { Link } from "react-router-dom";

export function PaperworkCenterPage() {
  return (
    <div className="admin-page">
      <header className="admin-page-header"><div><p className="admin-kicker">Administration</p><h1>Paperwork Center</h1><p>Daily, weekly, and monthly operational paperwork will live here as each approved form is published.</p></div></header>
      <section className="admin-paperwork-tabs" aria-label="Paperwork periods">
        <button className="is-active" type="button">Daily</button><button type="button" disabled>Weekly</button><button type="button" disabled>Monthly</button>
      </section>
      <section className="admin-paperwork-landing">
        <article><span className="admin-paperwork-icon" aria-hidden="true">▤</span><div><h2>NCU Days Count</h2><p>The browser-fillable Count Sheet is available now for officers and administrators.</p></div><Link className="admin-secondary-button" to="/count-sheet">Open Count Sheet</Link></article>
        <article className="is-planned"><span className="admin-paperwork-icon" aria-hidden="true">□</span><div><h2>Daily operational forms</h2><p>Assignment Roster, Uniform Inspection, detector tests, perimeter checks, searches, and sign-out sheets are the next application milestone. This page does not fabricate unfinished forms.</p></div><span className="admin-status-mark not-started">Next milestone</span></article>
      </section>
    </div>
  );
}
