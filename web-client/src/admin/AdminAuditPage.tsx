import { AlertTriangle, ArrowRight, CheckCircle2, Download, Filter, Search } from "lucide-react";
import { designPreviewEnabled } from "../api/client";
import { Button, PageHeader, Section } from "../components/ui";
import { previewAuditEvents } from "../data/preview";
import { AdminAdapterPending, formatDateTime } from "./shared";

export function AdminAuditPage() {
  if (!designPreviewEnabled) {
    return (
      <AdminAdapterPending
        title="Audit activity"
        description="Review allowlisted event metadata without exposing protected content."
      />
    );
  }
  return (
    <div className="page-stack admin-page">
      <PageHeader
        eyebrow="Accountability"
        title="Audit activity"
        description="Review allowlisted event metadata without exposing policy questions, report narratives, PINs, or credentials."
        actions={<Button variant="secondary" icon={<Download aria-hidden="true" />}>Export audit view</Button>}
      />
      <Section className="audit-page-section">
        <div className="report-toolbar">
          <label className="search-field"><Search aria-hidden="true" /><span className="sr-only">Search audit activity</span><input placeholder="Search action, actor, or target reference" /></label>
          <Button variant="secondary" icon={<Filter aria-hidden="true" />}>Filters</Button>
        </div>
        <div className="audit-timeline">
          {previewAuditEvents.map((event) => (
            <article key={event.id}>
              <span className={`audit-timeline__marker audit-timeline__marker--${event.result}`}>{event.result === "success" ? <CheckCircle2 aria-hidden="true" /> : <AlertTriangle aria-hidden="true" />}</span>
              <div className="audit-timeline__body">
                <div><strong>{event.action}</strong><span className={`audit-result-label audit-result-label--${event.result}`}>{event.result}</span></div>
                <p>{event.actor} · {event.target}</p>
                <time>{formatDateTime(event.createdAt)}</time>
              </div>
              <button className="button button--quiet button--sm"><span>Details</span><ArrowRight aria-hidden="true" /></button>
            </article>
          ))}
        </div>
      </Section>
    </div>
  );
}
