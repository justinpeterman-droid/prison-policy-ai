import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileClock,
  FileSearch,
  Gauge,
  RefreshCw,
  UserPlus,
  Users,
} from "lucide-react";
import { designPreviewEnabled } from "../api/client";
import { Button, Notice, PageHeader, ProgressBar, Section } from "../components/ui";
import { previewAuditEvents } from "../data/preview";
import { AdminAdapterPending, formatDateTime } from "./shared";

export function AdminOverviewPage() {
  if (!designPreviewEnabled) {
    return (
      <AdminAdapterPending
        title="Operations overview"
        description="Review account, report, audit, and platform conditions without exposing sensitive content."
      />
    );
  }
  return (
    <div className="page-stack admin-page">
      <PageHeader
        eyebrow="Administrator workspace"
        title="Operations overview"
        description="Review account, report, audit, and platform conditions without exposing sensitive content."
        actions={<Button variant="secondary" icon={<RefreshCw aria-hidden="true" />}>Refresh overview</Button>}
      />

      <Notice tone="info" title="Administrator actions are attributable">
        Sensitive account and report changes require purpose-specific PIN confirmation and create an audit record.
      </Notice>

      <div className="admin-overview-grid">
        <section className="admin-focus-card">
          <div className="admin-focus-card__header">
            <span className="admin-focus-card__icon"><Users aria-hidden="true" /></span>
            <div><p className="eyebrow eyebrow--light">Staff access</p><h2>1 account needs attention</h2></div>
          </div>
          <p>One Officer account is locked after failed sign-in attempts. Review before unlocking or resetting the PIN.</p>
          <Link className="button button--light button--md" to="/admin/staff">Review staff accounts <ArrowRight aria-hidden="true" /></Link>
        </section>

        <section className="admin-focus-card admin-focus-card--neutral">
          <div className="admin-focus-card__header">
            <span className="admin-focus-card__icon"><FileClock aria-hidden="true" /></span>
            <div><p className="eyebrow">Report oversight</p><h2>7 reports updated today</h2></div>
          </div>
          <p>Recent changes include two completed reports and one revision conflict resolved by an Administrator.</p>
          <Link className="text-link" to="/admin/reports">Open all reports <ArrowRight aria-hidden="true" /></Link>
        </section>
      </div>

      <div className="admin-dashboard-grid">
        <Section title="Platform health" description="Safe allowlisted service indicators.">
          <div className="health-summary">
            <div className="health-summary__status"><span className="health-dot health-dot--operational" /><div><strong>Core platform operational</strong><small>Database and web API responding normally.</small></div></div>
            <div className="health-components">
              <div><span>Database</span><strong><CheckCircle2 aria-hidden="true" /> Operational</strong></div>
              <div><span>AI job queue</span><strong><CheckCircle2 aria-hidden="true" /> Operational</strong></div>
              <div><span>Backup verification</span><strong className="health-warning"><AlertTriangle aria-hidden="true" /> Review due</strong></div>
            </div>
            <Link className="text-link" to="/admin/health">View system health <ArrowRight aria-hidden="true" /></Link>
          </div>
        </Section>

        <Section title="Recent audit activity" description="Fixed-schema events; report and policy contents are not displayed." action={<Link className="text-link" to="/admin/audit">View audit <ArrowRight aria-hidden="true" /></Link>}>
          <div className="audit-compact-list">
            {previewAuditEvents.slice(0, 4).map((event) => (
              <div key={event.id}>
                <span className={`audit-result audit-result--${event.result}`} aria-hidden="true" />
                <div><strong>{event.action}</strong><small>{event.actor} · {event.target}</small></div>
                <time>{formatDateTime(event.createdAt)}</time>
              </div>
            ))}
          </div>
        </Section>

        <Section title="AI workload" description="Current queue and recent execution state.">
          <div className="admin-job-overview">
            <div className="admin-job-overview__number"><strong>3</strong><span>Queued jobs</span></div>
            <ProgressBar value={28} label="Queue capacity" />
            <dl>
              <div><dt>Oldest queued job</dt><dd>2 minutes</dd></div>
              <div><dt>Completed today</dt><dd>41</dd></div>
              <div><dt>Failed today</dt><dd>1</dd></div>
            </dl>
          </div>
        </Section>

        <Section title="Administrator shortcuts" description="Actions remain server-authorized and step-up protected.">
          <div className="admin-shortcuts">
            <Link to="/admin/staff"><UserPlus aria-hidden="true" /><span><strong>Create an account</strong><small>Start from an approved roster identity.</small></span><ArrowRight aria-hidden="true" /></Link>
            <Link to="/admin/reports"><FileSearch aria-hidden="true" /><span><strong>Search all reports</strong><small>Review authorized report history.</small></span><ArrowRight aria-hidden="true" /></Link>
            <Link to="/admin/health"><Gauge aria-hidden="true" /><span><strong>Check platform health</strong><small>Review safe operational indicators.</small></span><ArrowRight aria-hidden="true" /></Link>
          </div>
        </Section>
      </div>
    </div>
  );
}
