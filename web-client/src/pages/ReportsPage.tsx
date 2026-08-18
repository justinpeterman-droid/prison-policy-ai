import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Bookmark,
  BookmarkCheck,
  CalendarDays,
  FilePlus2,
  Filter,
  RefreshCw,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { ApiError, designPreviewEnabled } from "../api/client";
import { Button, EmptyState, Notice, PageHeader, Section, SkeletonRows, StatusBadge } from "../components/ui";
import { previewReports } from "../data/preview";
import { listReports } from "../features/reports/reportApi";
import type { Relationship, ReportStatus, ReportSummary } from "../types";
import { useWorkspaceMemory } from "../workspace/WorkspaceMemoryProvider";

const statusOptions: Array<{ value: "all" | ReportStatus; label: string }> = [
  { value: "all", label: "All statuses" },
  { value: "in_progress", label: "In progress" },
  { value: "completed", label: "Completed" },
  { value: "archived", label: "Archived" },
];

function formatDate(value: string | null): string {
  if (!value) return "Not set";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function ReportsPage() {
  const [relationship, setRelationship] = useState<Relationship>("owned");
  const [status, setStatus] = useState<"all" | ReportStatus>("all");
  const [query, setQuery] = useState("");
  const [reports, setReports] = useState<ReportSummary[]>(
    designPreviewEnabled ? previewReports.filter((report) => report.relationship === "owned") : [],
  );
  const [loading, setLoading] = useState(!designPreviewEnabled);
  const [error, setError] = useState<string | null>(null);
  const { toggleReport, isReportSaved } = useWorkspaceMemory();

  const load = async () => {
    setError(null);
    if (designPreviewEnabled) {
      setReports(previewReports.filter((report) => report.relationship === relationship));
      return;
    }
    setLoading(true);
    try {
      setReports(await listReports(relationship, { status: status === "all" ? undefined : status }));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Reports could not be loaded.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [relationship, status]);

  const visibleReports = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return reports.filter((report) => {
      if (status !== "all" && report.status !== status) return false;
      if (!normalized) return true;
      return [
        report.reportType,
        report.category,
        report.reportingOfficerDisplayName,
        report.preparerDisplayName,
        report.reportId,
      ].some((value) => value?.toLowerCase().includes(normalized));
    });
  }, [reports, query, status]);

  return (
    <div className="page-stack reports-page">
      <PageHeader
        eyebrow="Report library"
        title="My reports"
        description="Find, resume, review, and export reports you own or prepared."
        actions={
          <Link className="button button--primary button--md" to="/reports/new">
            <FilePlus2 aria-hidden="true" /><span>New report</span>
          </Link>
        }
      />

      {error ? (
        <Notice tone="warning" title="Report list unavailable">
          <span>{error}</span>
          <Button variant="quiet" size="sm" onClick={() => void load()} icon={<RefreshCw aria-hidden="true" />}>Try again</Button>
        </Notice>
      ) : null}

      <Section className="report-library">
        <div className="report-library__tabs" role="tablist" aria-label="Report relationship">
          <button
            role="tab"
            aria-selected={relationship === "owned"}
            className={relationship === "owned" ? "active" : ""}
            onClick={() => setRelationship("owned")}
          >
            Owned by me
          </button>
          <button
            role="tab"
            aria-selected={relationship === "prepared"}
            className={relationship === "prepared" ? "active" : ""}
            onClick={() => setRelationship("prepared")}
          >
            Prepared by me
          </button>
        </div>

        <div className="report-toolbar">
          <label className="search-field">
            <Search aria-hidden="true" />
            <span className="sr-only">Search loaded reports</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search category, type, officer, or report ID"
            />
          </label>
          <label className="select-control">
            <Filter aria-hidden="true" />
            <span className="sr-only">Filter by status</span>
            <select value={status} onChange={(event) => setStatus(event.target.value as typeof status)}>
              {statusOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <Button variant="secondary" icon={<SlidersHorizontal aria-hidden="true" />}>More filters</Button>
        </div>

        {loading ? <SkeletonRows count={6} /> : visibleReports.length ? (
          <div className="data-table-wrap">
            <table className="data-table reports-table">
              <thead>
                <tr>
                  <th scope="col">Report</th>
                  <th scope="col">Incident date</th>
                  <th scope="col">Officer / preparer</th>
                  <th scope="col">Status</th>
                  <th scope="col">Updated</th>
                  <th scope="col"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {visibleReports.map((report) => {
                  const saved = isReportSaved(report.reportId);
                  return (
                    <tr key={report.reportId}>
                      <td>
                        <Link className="table-primary-link" to={`/reports/${report.reportId}`}>
                          <strong>{report.category ?? report.reportType}</strong>
                          <span>{report.reportType} · …{report.reportId.slice(-8)}</span>
                        </Link>
                      </td>
                      <td>
                        <span className="cell-with-icon"><CalendarDays aria-hidden="true" />{formatDate(report.incidentDate)}</span>
                      </td>
                      <td>
                        <strong className="cell-title">{report.reportingOfficerDisplayName}</strong>
                        <span className="cell-subtitle">Prepared by {report.preparerDisplayName}</span>
                      </td>
                      <td><StatusBadge status={report.status} /></td>
                      <td>
                        <strong className="cell-title">Rev. {report.currentRevisionNumber}</strong>
                        <span className="cell-subtitle">{formatDateTime(report.updatedAt)}</span>
                      </td>
                      <td>
                        <div className="table-actions">
                          <button
                            className="icon-button"
                            onClick={() => toggleReport(report)}
                            aria-label={saved ? "Remove saved report" : "Save report"}
                            title={saved ? "Remove saved report" : "Save report"}
                          >
                            {saved ? <BookmarkCheck aria-hidden="true" /> : <Bookmark aria-hidden="true" />}
                          </button>
                          <Link className="icon-button" to={`/reports/${report.reportId}`} aria-label="Open report" title="Open report">
                            <ArrowRight aria-hidden="true" />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={<FilePlus2 aria-hidden="true" />}
            title="No matching reports"
            description="Adjust the relationship, status, or search filter, or begin a new report."
            action={<Link className="button button--primary button--md" to="/reports/new"><FilePlus2 aria-hidden="true" /><span>Start a report</span></Link>}
          />
        )}
      </Section>
    </div>
  );
}
