import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Server } from "lucide-react";
import { EmptyState, PageHeader } from "../components/ui";

export const previewStaff = [
  { employee: "F-1007", name: "Lt. Avery Morgan", rank: "Lieutenant", shift: "A Shift", role: "admin", status: "Active" },
  { employee: "F-1042", name: "Officer Jordan Lee", rank: "Officer", shift: "B Shift", role: "officer", status: "Active" },
  { employee: "F-1064", name: "Officer Casey Rivers", rank: "Officer", shift: "C Shift", role: "officer", status: "Active" },
  { employee: "F-1098", name: "Officer Taylor Brooks", rank: "Officer", shift: "Utility", role: "officer", status: "Locked" },
  { employee: "F-1121", name: "Sgt. Morgan Quinn", rank: "Sergeant", shift: "D Shift", role: "officer", status: "No account" },
];

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function AdminAdapterPending({ title, description }: { title: string; description: string }) {
  return (
    <div className="page-stack admin-page">
      <PageHeader eyebrow="Administrator workspace" title={title} description={description} />
      <EmptyState
        icon={<Server aria-hidden="true" />}
        title="Browser administrator adapter pending"
        description="This foundation does not display fictional administrator records in live mode. Connect the server-authorized /web-api administrator routes before enabling this page."
      />
    </div>
  );
}

export function HealthCard({ icon, title, status, detail, warning = false }: { icon: ReactNode; title: string; status: string; detail: string; warning?: boolean }) {
  return (
    <article className={`health-card${warning ? " health-card--warning" : ""}`}>
      <span className="health-card__icon">{icon}</span>
      <div><h3>{title}</h3><span className="health-card__status">{warning ? <AlertTriangle aria-hidden="true" /> : <CheckCircle2 aria-hidden="true" />}{status}</span><p>{detail}</p></div>
    </article>
  );
}
