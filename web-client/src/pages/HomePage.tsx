import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpenCheck,
  CircleDot,
  Clock3,
  FilePlus2,
  MessageSquareText,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { ApiError, designPreviewEnabled } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { Button, Notice, PageHeader, ProgressBar, Section, SkeletonRows, StatusBadge } from "../components/ui";
import { previewJobs, previewReports } from "../data/preview";
import { listReports } from "../features/reports/reportApi";
import type { ReportSummary } from "../types";

function formatDate(value: string | null): string {
  if (!value) return "Date not set";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

function formatRelative(value: string): string {
  const milliseconds = Date.now() - new Date(value).getTime();
  const hours = Math.max(0, Math.round(milliseconds / 3_600_000));
  if (hours < 1) return "Updated recently";
  if (hours < 24) return `Updated ${hours}h ago`;
  const days = Math.round(hours / 24);
  return `Updated ${days}d ago`;
}

export function HomePage() {
  const { profile } = useAuth();
  const [reports, setReports] = useState<ReportSummary[]>(designPreviewEnabled ? previewReports : []);
  const [loading, setLoading] = useState(!designPreviewEnabled);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (designPreviewEnabled) return;
    setLoading(true);
    setError(null);
    try {
      const [owned, prepared] = await Promise.all([
        listReports("owned", { limit: 8 }),
        listReports("prepared", { limit: 4 }),
      ]);
      setReports([...owned, ...prepared].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Reports could not be loaded.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const activeDraft = useMemo(
    () => reports.find((report) => report.status === "in_progress"),
    [reports],
  );
  const recent = reports.slice(0, 5);
  const firstName = profile?.displayName.split(" ").at(-1) ?? "there";

  return (
    <div className="page-stack dashboard-page">
      <PageHeader
        eyebrow="Officer workspace"
        title={`Good afternoon, ${firstName}`}
        description="Continue your current work or begin a new policy question or incident report."
        actions={
          <div className="button-row">
            <Link className="button button--secondary button--md" to="/policy">
              <MessageSquareText aria-hidden="true" /><span>Ask Policy Expert</span>
            </Link>
            <Link className="button button--primary button--md" to="/reports/new">
              <FilePlus2 aria-hidden="true" /><span>Start a report</span>
            </Link>
          </div>
        }
      />

      {error ? (
        <Notice tone="warning" title="Some workspace data is unavailable">
          <span>{error}</span>
          <Button variant="quiet" size="sm" onClick={() => void load()} icon={<RefreshCw aria-hidden="true" />}>Try again</Button>
        </Notice>
      ) : null}

      <div className="dashboard-lead-grid">
        <section className="work-focus">
          <div className="work-focus__copy">
            <div className="work-focus__icon"><ShieldCheck aria-hidden="true" /></div>
            <p className="eyebrow eyebrow--light">Current work</p>
            <h2>{activeDraft ? activeDraft.category ?? activeDraft.reportType : "No report in progress"}</h2>
            <p>
              {activeDraft
                ? `Incident ${formatDate(activeDraft.incidentDate)} · Revision ${activeDraft.currentRevisionNumber}`
                : "Begin from field notes whenever you are ready."}
            </p>
          </div>
          <div className="work-focus__actions">
            {activeDraft ? (
              <Link className="button button--light button--md" to={`/reports/${activeDraft.reportId}`}>
                Continue report <ArrowRight aria-hidden="true" />
              </Link>
            ) : (
              <Link className="button button--light button--md" to="/reports/new">
                Start report <ArrowRight aria-hidden="true" />
              </Link>
            )}
            <span><Clock3 aria-hidden="true" /> {activeDraft ? formatRelative(activeDraft.updatedAt) : "Nothing pending"}</span>
          </div>
        </section>

        <section className="policy-quick-entry">
          <div>
            <p className="eyebrow">Policy Expert</p>
            <h2>Get a cited answer without leaving your workflow.</h2>
            <p>Ask about procedure, documentation, evidence handling, or report requirements.</p>
          </div>
          <div className="policy-quick-entry__prompt">
            <BookOpenCheck aria-hidden="true" />
            <span>“What must be documented when contraband is found during a barracks search?”</span>
          </div>
          <Link to="/policy" className="text-link">Open Policy Expert <ArrowRight aria-hidden="true" /></Link>
        </section>
      </div>

      <div className="dashboard-content-grid">
        <Section
          title="Recent reports"
          description="Your owned and prepared reports, newest activity first."
          action={<Link className="text-link" to="/reports">View all <ArrowRight aria-hidden="true" /></Link>}
          className="recent-reports"
        >
          {loading ? <SkeletonRows count={4} /> : (
            <div className="report-list" role="list">
              {recent.map((report) => (
                <Link className="report-list-item" to={`/reports/${report.reportId}`} key={report.reportId} role="listitem">
                  <span className="report-list-item__icon"><ClipboardIcon type={report.reportType} /></span>
                  <span className="report-list-item__main">
                    <strong>{report.category ?? report.reportType}</strong>
                    <small>{report.reportType} · {formatDate(report.incidentDate)}</small>
                  </span>
                  <StatusBadge status={report.status} />
                  <span className="report-list-item__meta">
                    <strong>Rev. {report.currentRevisionNumber}</strong>
                    <small>{formatRelative(report.updatedAt)}</small>
                  </span>
                  <ArrowRight className="report-list-item__arrow" aria-hidden="true" />
                </Link>
              ))}
              {!recent.length ? (
                <div className="inline-empty">
                  <FilePlus2 aria-hidden="true" />
                  <span><strong>No reports yet</strong><small>Your saved reports will appear here.</small></span>
                </div>
              ) : null}
            </div>
          )}
        </Section>

        <div className="dashboard-side-stack">
          <Section title="AI activity" description="Current report-processing work.">
            <div className="job-list">
              {designPreviewEnabled ? (
                previewJobs.slice(0, 2).map((job) => (
                  <div className="job-card" key={job.id}>
                    <div className="job-card__header">
                      <span className={`job-state-dot job-state-dot--${job.state}`} aria-hidden="true" />
                      <div>
                        <strong>{job.jobType === "generate" ? "Report generation" : "Fact extraction"}</strong>
                        <small>{job.stage}</small>
                      </div>
                      <StatusBadge status={job.state} />
                    </div>
                    {job.state === "running" ? <ProgressBar value={64} label="Processing" /> : null}
                  </div>
                ))
              ) : (
                <div className="inline-empty">
                  <Sparkles aria-hidden="true" />
                  <span>
                    <strong>Recent job summary pending</strong>
                    <small>The browser job-summary adapter must be connected before activity is shown here.</small>
                  </span>
                </div>
              )}
            </div>
          </Section>

          <Section title="Before you finalize" description="A quick trust-first review.">
            <ul className="review-checklist">
              <li><CircleDot aria-hidden="true" /><span>Verify names, identifiers, dates, and times.</span></li>
              <li><CircleDot aria-hidden="true" /><span>Separate observed facts from attributed statements.</span></li>
              <li><CircleDot aria-hidden="true" /><span>Resolve warnings before export or completion.</span></li>
            </ul>
            <div className="trust-note"><Sparkles aria-hidden="true" /><span>You remain the author and final reviewer.</span></div>
          </Section>
        </div>
      </div>
    </div>
  );
}

function ClipboardIcon({ type }: { type: string }) {
  return type.toLowerCase().includes("force") ? <ShieldCheck aria-hidden="true" /> : <FilePlus2 aria-hidden="true" />;
}
