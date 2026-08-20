import { Link } from "react-router-dom";
import type { DailyPaperworkKind, DailyRecordSummary } from "./api";


export interface DailyCardDefinition {
  kind: DailyPaperworkKind | "count_sheet";
  title: string;
  description: string;
  icon: string;
}


interface DailyRecordCardProps {
  definition: DailyCardDefinition;
  record?: DailyRecordSummary;
  workDate: string;
  shift: string;
}


function statusText(definition: DailyCardDefinition, record?: DailyRecordSummary): string {
  if (definition.kind === "count_sheet") return "Available";
  if (!record) return "Not started";
  if (record.state === "needs_attention") return "Needs attention";
  return `Saved · revision ${record.revision}`;
}


export function DailyRecordCard({ definition, record, workDate, shift }: DailyRecordCardProps) {
  const action = record || definition.kind === "count_sheet" ? "Open" : "Start";
  const href = definition.kind === "count_sheet"
    ? "/count-sheet"
    : `/admin/paperwork?tab=daily&work_date=${encodeURIComponent(workDate)}&shift=${encodeURIComponent(shift)}&kind=${definition.kind}${record ? `&record_id=${record.recordId}` : ""}`;

  return (
    <article className={`daily-record-card ${record?.state === "needs_attention" ? "needs-attention" : ""}`}>
      <span className="daily-record-icon" aria-hidden="true">{definition.icon}</span>
      <div className="daily-record-copy">
        <div className="daily-record-title-row">
          <h2>{definition.title}</h2>
          <span className={`daily-record-state ${record?.state ?? "not_started"}`}>{statusText(definition, record)}</span>
        </div>
        <p>{definition.description}</p>
        <dl>
          <div><dt>Date</dt><dd>{workDate}</dd></div>
          <div><dt>Shift</dt><dd>{shift}</dd></div>
          {record ? <div><dt>Revision</dt><dd>{record.revision}</dd></div> : null}
        </dl>
        {record?.warningCount ? (
          <p className="daily-record-warning">{record.warningCount} {record.warningCount === 1 ? "warning" : "warnings"}</p>
        ) : null}
      </div>
      <Link className="admin-secondary-button" to={href} aria-label={`${action} ${definition.title}`}>
        {action}
      </Link>
    </article>
  );
}
