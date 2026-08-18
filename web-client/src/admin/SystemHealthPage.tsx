import { Activity, AlertTriangle, RefreshCw, Server, ShieldCheck } from "lucide-react";
import { designPreviewEnabled } from "../api/client";
import { Button, PageHeader, Section } from "../components/ui";
import { AdminAdapterPending, HealthCard } from "./shared";

export function SystemHealthPage() {
  if (!designPreviewEnabled) {
    return (
      <AdminAdapterPending
        title="System health"
        description="Review safe platform status, queue conditions, and build identifiers."
      />
    );
  }
  return (
    <div className="page-stack admin-page">
      <PageHeader
        eyebrow="Operations"
        title="System health"
        description="Safe platform status, queue conditions, and build identifiers for operational review."
        actions={<Button variant="secondary" icon={<RefreshCw aria-hidden="true" />}>Refresh health</Button>}
      />

      <section className="system-health-hero">
        <span className="system-health-hero__icon"><Server aria-hidden="true" /></span>
        <div><p className="eyebrow eyebrow--light">Overall status</p><h2>Operational with one review item</h2><p>Core identity, report, and policy services are available. Backup verification requires administrative follow-up.</p></div>
        <span className="health-overall"><Activity aria-hidden="true" /> Operational</span>
      </section>

      <div className="health-card-grid">
        <HealthCard icon={<Server />} title="Database" status="Operational" detail="Connection and bounded count queries are responding normally." />
        <HealthCard icon={<Activity />} title="AI job queue" status="Operational" detail="Three jobs queued; oldest waiting time is under five minutes." />
        <HealthCard icon={<ShieldCheck />} title="Identity service" status="Operational" detail="Login, renewal, session revocation, and role checks responding." />
        <HealthCard icon={<AlertTriangle />} title="Backup verification" status="Review due" detail="Latest restore exercise status is not available in this snapshot." warning />
      </div>

      <div className="health-detail-grid">
        <Section title="Queue detail" description="Bounded operational indicators only.">
          <dl className="health-definition-list">
            <div><dt>Queued jobs</dt><dd>3</dd></div><div><dt>Pending outbox</dt><dd>2</dd></div><div><dt>Oldest queue age</dt><dd>2 minutes</dd></div><div><dt>Recent failures</dt><dd>1</dd></div>
          </dl>
        </Section>
        <Section title="Build information" description="Safe deployment identifiers.">
          <dl className="health-definition-list">
            <div><dt>API version</dt><dd>v1</dd></div><div><dt>Release</dt><dd>Web companion candidate</dd></div><div><dt>Environment</dt><dd>Review lab</dd></div><div><dt>Last checked</dt><dd>Just now</dd></div>
          </dl>
        </Section>
      </div>
    </div>
  );
}
