import { Link } from "react-router-dom";
import { SaveState, type EditorSaveState } from "./SaveState";


interface DailyEditorHeaderProps {
  title: string;
  workDate: string;
  shift: string;
  saveState: EditorSaveState;
  onSave?: () => void;
  onPreview?: () => void;
  onPrint?: () => void;
}


export function DailyEditorHeader(props: DailyEditorHeaderProps) {
  return (
    <header className="daily-editor-header">
      <div>
        <Link className="admin-back-link" to={`/admin/paperwork?tab=daily&work_date=${props.workDate}&shift=${props.shift}`}>← Back to Daily Paperwork</Link>
        <p className="admin-kicker">Daily operational paperwork</p>
        <h1>{props.title}</h1>
        <p>{props.workDate} · {props.shift} Shift</p>
      </div>
      <div className="daily-editor-actions">
        <SaveState state={props.saveState} />
        <button type="button" className="admin-secondary-button" onClick={props.onSave} disabled={!props.onSave}>Save Now</button>
        <button type="button" className="admin-secondary-button" onClick={props.onPreview} disabled={!props.onPreview}>Preview</button>
        <button type="button" className="admin-primary-button" onClick={props.onPrint} disabled={!props.onPrint}>Print</button>
      </div>
    </header>
  );
}
