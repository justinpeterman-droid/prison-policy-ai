import { Link } from "react-router-dom";
import { DocumentStudioPage } from "../../incidents/DocumentStudioPage";
import { AdminAttributionBanner } from "./AdminAttributionBanner";

export function AdminIncidentWorkspace() {
  return (
    <div className="admin-incident-workspace">
      <div className="admin-incident-toolbar">
        <Link to="/admin/incidents" className="admin-back-link">← All Incidents</Link>
        <span>Administrator review context</span>
      </div>
      <AdminAttributionBanner />
      <DocumentStudioPage />
    </div>
  );
}
