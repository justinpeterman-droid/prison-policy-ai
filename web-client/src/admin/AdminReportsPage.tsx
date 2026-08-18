import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Download, Filter, Search } from "lucide-react";
import { designPreviewEnabled } from "../api/client";
import { Button, PageHeader, Section, StatusBadge } from "../components/ui";
import { previewReports } from "../data/preview";
import { AdminAdapterPending, formatDateTime } from "./shared";

export function AdminReportsPage() {
  const [query, setQuery] = useState("");
  const visible = useMemo(() => {
    const value = query.trim().toLowerCase();
    const all = [...previewReports, ...previewReports.map((report, index) => ({ ...report, reportId: `${report.reportId.slice(0, -1)}${index + 5}`, reportingOfficerDisplayName: index % 2 ? "Officer Taylor Brooks" : "Officer Casey Rivers" }))];
    return value ? all.filter((report) => [report.category, report.reportType, report.reportingOfficerDisplayName, report.reportId].some((item) => item?.toLowerCase().includes(value))) : all;
  }, [query]);

  if (!designPreviewEnabled) {
    return (
      <AdminAdapterPending
        title="All reports"
        description="Search authorized reports across Officers while preserving ownership and revision attribution."
      />
    );
  }

  return (
    <div className="page-stack admin-page">
      <PageHeader
        eyebrow="Organization-wide oversight"
        title="All reports"
        description="Search authorized reports across Officers while preserving ownership and revision attribution."
        actions={<Button variant="secondary" icon={<Download aria-hidden="true" />}>Bulk export</Button>}
      />
      <Section className="admin-table-section">
        <div className="report-toolbar">
          <label className="search-field"><Search aria-hidden="true" /><span className="sr-only">Search all reports</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search report, category, owner, or ID" /></label>
          <Button variant="secondary" icon={<Filter aria-hidden="true" />}>Filters</Button>
        </div>
        <div className="data-table-wrap">
          <table className="data-table reports-table">
            <thead><tr><th>Report</th><th>Owner</th><th>Status</th><th>Revision</th><th>Updated</th><th><span className="sr-only">Open</span></th></tr></thead>
            <tbody>
              {visible.map((report) => (
                <tr key={report.reportId}>
                  <td><strong className="cell-title">{report.category ?? report.reportType}</strong><span className="cell-subtitle">{report.reportType} · …{report.reportId.slice(-8)}</span></td>
                  <td><strong className="cell-title">{report.reportingOfficerDisplayName}</strong><span className="cell-subtitle">Prepared by {report.preparerDisplayName}</span></td>
                  <td><StatusBadge status={report.status} /></td>
                  <td>Revision {report.currentRevisionNumber}</td>
                  <td>{formatDateTime(report.updatedAt)}</td>
                  <td><Link className="icon-button" to={`/reports/${report.reportId}`} aria-label="Open report"><ArrowRight aria-hidden="true" /></Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}
