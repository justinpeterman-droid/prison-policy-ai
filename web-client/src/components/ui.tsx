import type { ButtonHTMLAttributes, PropsWithChildren, ReactNode } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  CircleAlert,
  Info,
  LoaderCircle,
  X,
} from "lucide-react";
import type { ReportStatus } from "../types";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div className="page-header__copy">
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
        {description ? <p className="page-header__description">{description}</p> : null}
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}

export function Section({
  title,
  description,
  action,
  children,
  className = "",
}: PropsWithChildren<{
  title?: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}>) {
  return (
    <section className={`section-card ${className}`.trim()}>
      {title || description || action ? (
        <div className="section-card__header">
          <div>
            {title ? <h2>{title}</h2> : null}
            {description ? <p>{description}</p> : null}
          </div>
          {action ? <div>{action}</div> : null}
        </div>
      ) : null}
      <div className="section-card__body">{children}</div>
    </section>
  );
}

export function Button({
  variant = "primary",
  size = "md",
  icon,
  children,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "quiet" | "danger";
  size?: "sm" | "md";
  icon?: ReactNode;
}) {
  return (
    <button
      className={`button button--${variant} button--${size} ${className}`.trim()}
      {...props}
    >
      {icon ? <span className="button__icon">{icon}</span> : null}
      <span>{children}</span>
    </button>
  );
}

export function StatusBadge({ status }: { status: ReportStatus | "running" | "succeeded" | "failed" | "queued" }) {
  const labels: Record<string, string> = {
    in_progress: "In progress",
    completed: "Completed",
    archived: "Archived",
    running: "Running",
    succeeded: "Completed",
    failed: "Needs attention",
    queued: "Queued",
  };
  return <span className={`status status--${status}`}>{labels[status] ?? status}</span>;
}

export function Notice({
  tone = "info",
  title,
  children,
}: PropsWithChildren<{ tone?: "info" | "success" | "warning" | "danger"; title?: string }>) {
  const icon = {
    info: <Info aria-hidden="true" />,
    success: <CheckCircle2 aria-hidden="true" />,
    warning: <AlertTriangle aria-hidden="true" />,
    danger: <CircleAlert aria-hidden="true" />,
  }[tone];
  return (
    <div className={`notice notice--${tone}`} role={tone === "danger" ? "alert" : "status"}>
      <span className="notice__icon">{icon}</span>
      <div>
        {title ? <strong>{title}</strong> : null}
        <div>{children}</div>
      </div>
    </div>
  );
}

export function LoadingState({ label = "Loading workspace" }: { label?: string }) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <LoaderCircle className="spin" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      {icon ? <div className="empty-state__icon">{icon}</div> : null}
      <h3>{title}</h3>
      <p>{description}</p>
      {action ? <div className="empty-state__action">{action}</div> : null}
    </div>
  );
}

export function ProgressBar({ value, label }: { value: number; label: string }) {
  const bounded = Math.min(100, Math.max(0, value));
  return (
    <div className="progress" aria-label={label}>
      <div className="progress__meta">
        <span>{label}</span>
        <strong>{bounded}%</strong>
      </div>
      <div className="progress__track" aria-hidden="true">
        <span style={{ width: `${bounded}%` }} />
      </div>
    </div>
  );
}

export function Drawer({
  open,
  title,
  onClose,
  children,
}: PropsWithChildren<{ open: boolean; title: string; onClose(): void }>) {
  if (!open) return null;
  return (
    <div className="drawer-layer" role="presentation">
      <button className="drawer-layer__backdrop" aria-label="Close panel" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={title}>
        <div className="drawer__header">
          <h2>{title}</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close panel">
            <X aria-hidden="true" />
          </button>
        </div>
        <div className="drawer__body">{children}</div>
      </aside>
    </div>
  );
}

export function SkeletonRows({ count = 3 }: { count?: number }) {
  return (
    <div className="skeleton-list" aria-hidden="true">
      {Array.from({ length: count }, (_, index) => (
        <div className="skeleton-row" key={index}>
          <span />
          <span />
          <span />
        </div>
      ))}
    </div>
  );
}
