import type { DailyRecordSummary } from "./api";
import { DailyRecordCard, type DailyCardDefinition } from "./DailyRecordCard";


export const DAILY_CARD_DEFINITIONS: readonly DailyCardDefinition[] = [
  { kind: "assignment_roster", title: "Shift Assignment Roster", description: "Assign active staff to approved posts, rotations, leave, and shift briefing duties.", icon: "▦" },
  { kind: "uniform_inspection", title: "Uniform Inspection", description: "Inspect rostered staff using the approved uniform categories and comment requirements.", icon: "◇" },
  { kind: "count_sheet", title: "NCU Days Count", description: "Open the existing officer and administrator population Count Sheet.", icon: "∑" },
  { kind: "metal_detector_test", title: "Walk-Through Metal Detector Testing", description: "Record daily pass or fail results across eleven detectors and seven test positions.", icon: "⌁" },
  { kind: "perimeter_check", title: "Daily Perimeter Checklist", description: "Complete the approved doors, outside doors, fence, gates, and supporting checks.", icon: "⬡" },
  { kind: "random_search_log", title: "Daily Random Searches", description: "Record the four approved search blocks for each housing section.", icon: "⌕" },
  { kind: "detector_sign_out", title: "Handheld Detector Sign-Out", description: "Assign handheld detector units D1 through D9 to staff and work areas.", icon: "↗" },
] as const;


interface DailyPaperworkTabProps {
  workDate: string;
  shift: string;
  records: DailyRecordSummary[];
  loading: boolean;
  error: string | null;
}


export function DailyPaperworkTab({ workDate, shift, records, loading, error }: DailyPaperworkTabProps) {
  const byKind = new Map(records.map((record) => [record.kind, record]));
  return (
    <section id="paperwork-panel-daily" role="tabpanel" aria-labelledby="paperwork-tab-daily">
      {error ? <div className="admin-alert error" role="alert">{error}</div> : null}
      {loading ? <div className="admin-loading-panel" aria-busy="true">Searching saved daily records…</div> : null}
      <div className="daily-record-grid" data-testid="daily-record-grid">
        {DAILY_CARD_DEFINITIONS.map((definition) => (
          <DailyRecordCard
            key={definition.kind}
            definition={definition}
            record={definition.kind === "count_sheet" ? undefined : byKind.get(definition.kind)}
            workDate={workDate}
            shift={shift}
          />
        ))}
      </div>
    </section>
  );
}
