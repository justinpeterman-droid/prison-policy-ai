import { DETECTOR_CODES, DETECTOR_POSITIONS, type MetalPayload } from "./model";


export function MetalDetectorPrint({ payload }: { payload: MetalPayload }) {
  return <article className="metal-detector-print" data-testid="metal-detector-print" aria-label="Metal Detector Test print document">
    <header><div><strong>North Central Unit</strong><span>Daily operational paperwork</span></div><h1>Daily Walk-Through Metal Detector Testing</h1><dl><dt>Date</dt><dd>{payload.work_date}</dd><dt>Shift</dt><dd>{payload.shift}</dd></dl></header>
    <table><thead><tr><th>Test Position</th>{DETECTOR_CODES.map((code) => <th key={code}>{code}</th>)}</tr></thead><tbody>{DETECTOR_POSITIONS.map((position, positionIndex) => <tr key={position}><th>{position}</th>{payload.detectors.map((detector) => <td key={detector.detector_code}>{detector.tests[positionIndex].result ?? "—"}</td>)}</tr>)}</tbody></table>
    <p className="metal-print-legend"><strong>P = Pass</strong><strong>F = Fail</strong><span>Detector numbers correspond to the documented test locations and equipment identifiers below.</span></p>
    <section><h2>Location / Equipment Identifier</h2><div className="metal-print-details">{payload.detectors.map((detector) => <p key={detector.detector_code}><strong>{detector.detector_code}</strong> {detector.location || "—"} / {detector.equipment_identifier || "—"}</p>)}</div></section>
    <section><h2>Comments, including Corrective Action Taken</h2>{payload.detectors.filter((detector) => detector.corrective_action).map((detector) => <p key={detector.detector_code}><strong>Detector {detector.detector_code}:</strong> {detector.corrective_action}</p>)}<p>{payload.comments || "—"}</p></section>
    <div className="metal-print-signoff"><span>Tested by: {payload.tested_by?.display_name_snapshot ?? "________________"}</span><span>Reviewed By: {payload.reviewed_by?.display_name_snapshot ?? "________________"}</span></div>
    <footer><strong>Distribution:</strong> Shift Supervisor · Building Captain · File</footer>
  </article>;
}
