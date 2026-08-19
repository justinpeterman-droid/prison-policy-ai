import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { WebApiError } from "../../api/client";
import { listIncidents, type IncidentPage, type IncidentSummary } from "./api";

function displayIncidentNumber(value: string | null): string {
  return value || "Unnumbered Incident";
}

function displayIncidentName(value: string | null): string {
  return value || "Incident name not assigned";
}

function displayDate(value: string | null): string {
  if (!value) return "Date not entered";
  const date = new Date(`${value}T12:00:00`);
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function officers(item: IncidentSummary): string {
  if (!item.reporting_officers.length) return "No reporting officer selected";
  return item.reporting_officers.map((officer) => officer.display_name).join(", ");
}

function countLabel(value: number, singular: string, plural: string): string {
  return `${value} ${value === 1 ? singular : plural}`;
}

function IncidentCard({ item }: { item: IncidentSummary }) {
  return (
    <article className="iw-incident-card">
      <div className="iw-incident-card-main">
        <div>
          <p className="iw-number">{displayIncidentNumber(item.incident_number)}</p>
          <h2>{displayIncidentName(item.incident_name)}</h2>
        </div>
        <span className={`iw-progress iw-progress-${item.progress.code}`}>
          {item.progress.label}
        </span>
      </div>
      <dl className="iw-incident-facts">
        <div><dt>Date</dt><dd>{displayDate(item.incident_date)}</dd></div>
        <div><dt>Location</dt><dd>{item.location || "Not entered"}</dd></div>
        <div><dt>Category</dt><dd>{item.category?.replaceAll("_", " ") || "Not classified"}</dd></div>
        <div><dt>Officers</dt><dd>{officers(item)}</dd></div>
      </dl>
      <div className="iw-incident-card-footer">
        <div className="iw-document-counts">
          <span>{countLabel(item.officer_report_count, "officer report", "officer reports")}</span>
          <span>{countLabel(item.required_paperwork_count, "required item", "required items")}</span>
        </div>
        <Link
          className="iw-button iw-button-primary"
          to={`/reports/${item.incident_id}`}
          aria-label={`Open incident ${displayIncidentNumber(item.incident_number)}`}
        >
          Open Incident
        </Link>
      </div>
    </article>
  );
}

export function ReportsPage() {
  const [query, setQuery] = useState("");
  const [relationship, setRelationship] = useState("all");
  const [page, setPage] = useState<IncidentPage>({ items: [], next_cursor: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError(null);
      void listIncidents({ q: query, relationship }).then(
        (result) => {
          if (!active) return;
          setPage(result);
          setLoading(false);
        },
        (reason: unknown) => {
          if (!active) return;
          setLoading(false);
          setError(
            reason instanceof WebApiError
              ? reason.message
              : "The incident library could not be loaded.",
          );
        },
      );
    }, query ? 220 : 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [query, relationship, refreshToken]);

  const summary = useMemo(() => {
    if (loading) return "Loading authorized incidents…";
    if (page.items.length === 1) return "1 incident";
    return `${page.items.length} incidents`;
  }, [loading, page.items.length]);

  return (
    <section className="iw-page" aria-labelledby="reports-heading">
      <header className="iw-page-header">
        <div>
          <p className="iw-eyebrow">Incident-centered workspace</p>
          <h1 id="reports-heading">Reports</h1>
          <p>
            Find every report, form, and required action under its official incident
            number and descriptive name.
          </p>
        </div>
        <Link className="iw-button iw-button-gold" to="/new-report">
          Start New Incident
        </Link>
      </header>

      <div className="iw-filter-bar">
        <label className="iw-field iw-search-field">
          <span>Search incidents</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Number, name, officer, category, or location"
          />
        </label>
        <label className="iw-field">
          <span>Incident relationship</span>
          <select
            value={relationship}
            onChange={(event) => setRelationship(event.target.value)}
          >
            <option value="all">All incidents I can access</option>
            <option value="reporting">I am a reporting officer</option>
            <option value="prepared">I prepared for another officer</option>
          </select>
        </label>
        <div className="iw-filter-summary" role="status" aria-live="polite">
          {summary}
        </div>
      </div>

      {error ? (
        <div className="iw-callout iw-callout-error" role="alert">
          <div>
            <strong>Reports could not be loaded</strong>
            <p>{error}</p>
          </div>
          <button
            className="iw-button iw-button-secondary"
            type="button"
            onClick={() => setRefreshToken((value) => value + 1)}
          >
            Try Again
          </button>
        </div>
      ) : null}

      {loading ? (
        <div className="iw-loading-grid" aria-label="Loading incidents" aria-busy="true">
          <span /><span /><span />
        </div>
      ) : null}

      {!loading && !error && page.items.length === 0 ? (
        <div className="iw-empty-state">
          <div className="iw-empty-icon" aria-hidden="true">◎</div>
          <h2>No incidents match this view</h2>
          <p>Change the search or relationship filter, or start a new incident.</p>
          <Link className="iw-button iw-button-gold" to="/new-report">
            Start New Incident
          </Link>
        </div>
      ) : null}

      {!loading && page.items.length ? (
        <div className="iw-incident-list">
          {page.items.map((item) => (
            <IncidentCard key={item.incident_id} item={item} />
          ))}
        </div>
      ) : null}
    </section>
  );
}
