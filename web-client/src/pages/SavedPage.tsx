import { Link } from "react-router-dom";
import {
  ArrowRight,
  Bookmark,
  BookOpenCheck,
  FileText,
  MessageSquareText,
  Trash2,
} from "lucide-react";
import { EmptyState, PageHeader, Section, StatusBadge } from "../components/ui";
import { useWorkspaceMemory } from "../workspace/WorkspaceMemoryProvider";

export function SavedPage() {
  const { savedCitations, savedReports, removeCitation, toggleReport } = useWorkspaceMemory();
  const empty = !savedCitations.length && !savedReports.length;

  return (
    <div className="page-stack saved-page">
      <PageHeader
        eyebrow="Session workspace"
        title="Saved"
        description="Keep useful reports and policy passages together while you are signed in. Saved items are cleared at sign-out."
      />

      {empty ? (
        <EmptyState
          icon={<Bookmark aria-hidden="true" />}
          title="Nothing saved in this session"
          description="Save a report from My Reports or a citation from Policy Expert to place it here temporarily."
          action={<Link className="button button--primary button--md" to="/policy"><MessageSquareText aria-hidden="true" /><span>Ask Policy Expert</span></Link>}
        />
      ) : (
        <div className="saved-grid">
          <Section title="Saved reports" description="Quick links to reports in your authorized workspace.">
            {savedReports.length ? (
              <div className="saved-list">
                {savedReports.map((report) => (
                  <div className="saved-list-item" key={report.reportId}>
                    <span className="saved-list-item__icon"><FileText aria-hidden="true" /></span>
                    <div className="saved-list-item__copy">
                      <strong>{report.category ?? report.reportType}</strong>
                      <span>{report.reportType} · Revision {report.currentRevisionNumber}</span>
                    </div>
                    <StatusBadge status={report.status} />
                    <button className="icon-button" onClick={() => toggleReport(report)} aria-label="Remove saved report"><Trash2 aria-hidden="true" /></button>
                    <Link className="icon-button" to={`/reports/${report.reportId}`} aria-label="Open report"><ArrowRight aria-hidden="true" /></Link>
                  </div>
                ))}
              </div>
            ) : (
              <div className="inline-empty"><FileText aria-hidden="true" /><span><strong>No saved reports</strong><small>Use the bookmark action in My Reports.</small></span></div>
            )}
          </Section>

          <Section title="Saved policy passages" description="Citations kept only for the active signed-in session.">
            {savedCitations.length ? (
              <div className="saved-citation-list">
                {savedCitations.map((citation) => (
                  <article key={`${citation.source}-${citation.n}`}>
                    <div className="saved-citation-list__header">
                      <span><BookOpenCheck aria-hidden="true" />[{citation.n}] {citation.source}</span>
                      <button className="icon-button" onClick={() => removeCitation(citation.source, citation.n)} aria-label="Remove saved citation"><Trash2 aria-hidden="true" /></button>
                    </div>
                    <blockquote>{citation.text}</blockquote>
                  </article>
                ))}
              </div>
            ) : (
              <div className="inline-empty"><BookOpenCheck aria-hidden="true" /><span><strong>No saved passages</strong><small>Open a numbered citation in Policy Expert and save it for this session.</small></span></div>
            )}
          </Section>
        </div>
      )}
    </div>
  );
}
