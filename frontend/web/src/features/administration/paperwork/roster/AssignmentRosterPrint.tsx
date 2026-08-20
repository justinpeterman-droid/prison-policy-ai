import { displayStaff, ROSTER_DEFINITION, type RosterPayload } from "./model";


interface AssignmentRosterPrintProps {
  payload: RosterPayload;
}

const EQUIPMENT = [
  ["digital_camera", "Digital Camera"],
  ["video_camera_go_pro", "Video Camera (Go PRO)"],
  ["metal_detector_wands", "9 Metal Detector Wands"],
] as const;

export function AssignmentRosterPrint({ payload }: AssignmentRosterPrintProps) {
  return (
    <article className="assignment-roster-print" data-testid="assignment-roster-print" aria-label="Assignment Roster print document">
      <header>
        <div><strong>{ROSTER_DEFINITION.facility_label}</strong><span>Shift Personnel and Housing Zones</span></div>
        <h1>Shift Assignment Roster</h1>
        <dl><div><dt>Date</dt><dd>{payload.work_date}</dd></div><div><dt>Shift</dt><dd>{payload.shift}</dd></div></dl>
      </header>
      <div className="roster-print-columns">
        <main>
          {payload.zones.map((zone) => {
            const definition = ROSTER_DEFINITION.zones.find((item) => item.code === zone.zone_code)!;
            return (
              <section key={zone.zone_code}>
                <div className="roster-print-zone-heading">
                  <h2>{definition.label}</h2><span>{definition.area}</span><strong>{definition.supervisor_label}: {zone.supervisor?.display_name_snapshot ?? "—"}</strong>
                </div>
                <table>
                  <thead><tr><th>Priority</th><th>Post</th><th>Initial Officer</th><th>Rotation Officer</th></tr></thead>
                  <tbody>
                    {zone.posts.map((assignment) => {
                      const item = definition.posts.find((candidate) => candidate.code === assignment.post_code)!;
                      return <tr key={assignment.post_code}><td>{item.priority}</td><th>{item.label}</th><td>{displayStaff(assignment.initial_staff, assignment.initial_state)}</td><td>{displayStaff(assignment.rotation_staff, assignment.rotation_state)}</td></tr>;
                    })}
                  </tbody>
                </table>
              </section>
            );
          })}
        </main>
        <aside>
          <section><h2>Shift command</h2><p><strong>Captain:</strong> {payload.captain?.display_name_snapshot ?? "—"}</p><p><strong>Lieutenant:</strong> {payload.lieutenant?.display_name_snapshot ?? "—"}</p><p><strong>Duty Warden:</strong> {payload.duty_warden || "—"}</p><p><strong>Alternate Shift Supervisor:</strong> {payload.alternate_shift_supervisor?.display_name_snapshot ?? "—"}</p></section>
          <section><h2>Leave Time (Type of Leave)</h2>{payload.leave_entries.length ? payload.leave_entries.map((entry, index) => <p key={`${entry.staff.staff_id}-${index}`}>{entry.staff.display_name_snapshot} · {entry.leave_time} ({entry.leave_type})</p>) : <p>—</p>}</section>
          <section><h2>Extra Assignments</h2>{payload.extra_assignments.length ? payload.extra_assignments.map((entry, index) => <p key={`${entry.label}-${index}`}>{entry.label}: {entry.staff?.display_name_snapshot ?? "—"}</p>) : <p>—</p>}</section>
          <section><h2>Security Equipment Accounted For</h2>{EQUIPMENT.map(([key, label]) => <p key={key}>{label}: {payload.equipment[key].replace("_", " ")}</p>)}</section>
          <section><h2>Shift checks</h2><p>Roll Call: {payload.roll_call_completed ? "Completed" : "Incomplete"}</p><p>Uniform Inspection: {payload.uniform_inspection_completed ? "Completed" : "Incomplete"}</p><p>Assigned to post and dismissed: {payload.assigned_and_dismissed ? "Yes" : "No"}</p></section>
          <section><h2>Guests at Shift Briefing</h2><p>{payload.briefing_guests.join(", ") || "—"}</p></section>
        </aside>
      </div>
      <section className="roster-print-notes"><h2>Shift Briefing Minutes</h2><p>{payload.briefing_minutes || "—"}</p></section>
      <p className="roster-priority-warning">{ROSTER_DEFINITION.priority_one_warning}</p>
      <div className="roster-print-signatures"><span>Lieutenant Signature: {payload.lieutenant_signature_name || "____________________"}</span><span>Date: {payload.work_date}</span></div>
      <footer><p>{ROSTER_DEFINITION.notes.join(" · ")}</p><p><strong>Distribution:</strong> {ROSTER_DEFINITION.distribution.join(" · ")}</p></footer>
    </article>
  );
}
