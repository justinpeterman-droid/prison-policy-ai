import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, ChevronRight } from "lucide-react";
import { Section, StatusBadge } from "../../components/ui";
import type { ReportDetail } from "../../types";

export function ReportContext({ report, warnings }: { report: ReportDetail; warnings: string[] }) {
  return (
    <aside className="workspace-context" aria-label="Report context">
      <Section title="Report status">
        <dl className="compact-details">
          <div><dt>Status</dt><dd><StatusBadge status={report.status} /></dd></div>
          <div><dt>Revision</dt><dd>{report.currentRevisionNumber || "Unsaved"}</dd></div>
          <div><dt>Owner</dt><dd>{report.reportingOfficerDisplayName}</dd></div>
          <div><dt>Last editor</dt><dd>{report.lastEditorDisplayName}</dd></div>
        </dl>
      </Section>
      <Section title="Review warnings">
        {warnings.length ? (
          <ul className="warning-list">{warnings.map((warning) => <li key={warning}><AlertTriangle aria-hidden="true" /><span>{warning}</span></li>)}</ul>
        ) : (
          <div className="compact-success"><CheckCircle2 aria-hidden="true" /><span>No unresolved warnings.</span></div>
        )}
      </Section>
      <Section title="Policy help">
        <p className="context-copy">Ask a policy question in a separate cited workspace without losing this draft.</p>
        <Link className="text-link" to="/policy">Open Policy Expert <ChevronRight aria-hidden="true" /></Link>
      </Section>
    </aside>
  );
}
