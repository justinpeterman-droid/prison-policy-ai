import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { DailyPaperworkTab } from "./DailyPaperworkTab";
import { DailyRecordWorkspace } from "./DailyRecordWorkspace";
import { dailyPaperworkKindSchema } from "./schemas";
import { fetchDailyPaperwork, type DailyRecordSummary } from "./api";
import { MonthlyPaperworkTab } from "./MonthlyPaperworkTab";
import { WeeklyPaperworkTab } from "./WeeklyPaperworkTab";
import "./paperwork-center.css";


type Period = "daily" | "weekly" | "monthly";
const PERIODS: Period[] = ["daily", "weekly", "monthly"];


function localDate(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

export function PaperworkCenterPage() {
  const [params, setParams] = useSearchParams();
  const rawTab = params.get("tab");
  const tab: Period = rawTab === "weekly" || rawTab === "monthly" ? rawTab : "daily";
  const workDate = params.get("work_date") ?? localDate();
  const shift = params.get("shift") ?? "D";
  const parsedKind = dailyPaperworkKindSchema.safeParse(params.get("kind"));
  const kind = parsedKind.success ? parsedKind.data : null;
  const recordId = params.get("record_id");
  const [records, setRecords] = useState<DailyRecordSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (tab !== "daily" || kind) return;
    let active = true;
    setLoading(true);
    setError(null);
    void fetchDailyPaperwork(workDate, shift)
      .then((page) => { if (active) setRecords(page.items); })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Saved daily records could not be searched.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [kind, shift, tab, workDate]);

  function update(values: Record<string, string | null>) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(values)) {
      if (value === null) next.delete(key);
      else next.set(key, value);
    }
    setParams(next);
  }

  function choosePeriod(next: Period) {
    update({ tab: next, kind: null, record_id: null });
  }

  function handleTabKey(event: React.KeyboardEvent<HTMLButtonElement>, current: Period) {
    let index = PERIODS.indexOf(current);
    if (event.key === "ArrowRight") index = (index + 1) % PERIODS.length;
    else if (event.key === "ArrowLeft") index = (index + PERIODS.length - 1) % PERIODS.length;
    else if (event.key === "Home") index = 0;
    else if (event.key === "End") index = PERIODS.length - 1;
    else return;
    event.preventDefault();
    const next = PERIODS[index];
    choosePeriod(next);
    window.requestAnimationFrame(() => document.getElementById(`paperwork-tab-${next}`)?.focus());
  }

  if (kind) {
    return <DailyRecordWorkspace kind={kind} recordId={recordId} workDate={workDate} shift={shift} />;
  }

  return (
    <div className="admin-page">
      <header className="admin-page-header"><div><p className="admin-kicker">Administration</p><h1>Paperwork Center</h1><p>Search, reopen, complete, and print operational paperwork by date and shift.</p></div></header>
      <section className="admin-paperwork-tabs" role="tablist" aria-label="Paperwork periods">
        {PERIODS.map((period) => (
          <button
            key={period}
            id={`paperwork-tab-${period}`}
            className={tab === period ? "is-active" : ""}
            type="button"
            role="tab"
            aria-selected={tab === period}
            aria-controls={`paperwork-panel-${period}`}
            tabIndex={tab === period ? 0 : -1}
            onClick={() => choosePeriod(period)}
            onKeyDown={(event) => handleTabKey(event, period)}
          >{period[0].toUpperCase() + period.slice(1)}</button>
        ))}
      </section>
      {tab === "daily" ? <section className="paperwork-filters" aria-label="Daily paperwork search">
        <label>Work date<input aria-label="Work date" type="date" value={workDate} onChange={(event) => update({ work_date: event.target.value })} /></label>
        <label>Shift<select aria-label="Shift" value={shift} onChange={(event) => update({ shift: event.target.value })}><option value="A">A — Day</option><option value="B">B — Day</option><option value="C">C — Night</option><option value="D">D — Night</option><option value="U">U — Utility</option><option value="F">F — Field</option></select></label>
      </section> : null}
      {tab === "daily" ? <DailyPaperworkTab workDate={workDate} shift={shift} records={records} loading={loading} error={error} /> : null}
      {tab === "weekly" ? <WeeklyPaperworkTab /> : null}
      {tab === "monthly" ? <MonthlyPaperworkTab /> : null}
    </div>
  );
}
