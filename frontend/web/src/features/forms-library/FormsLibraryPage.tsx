import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  fetchFormsLibrary,
  type FormLibraryItem,
  type FormOutputKind,
  type FormsLibraryFilters,
} from "./api";
import "./forms-library.css";

interface FormsLibraryPageProps {
  onPreview?: (item: FormLibraryItem) => void;
  onPrint?: (item: FormLibraryItem) => void;
  onDownloadWord?: (item: FormLibraryItem) => void;
  onDownloadPdf?: (item: FormLibraryItem) => void;
  onAddToIncident?: (item: FormLibraryItem) => void;
}

const EMPTY_FILTERS: FormsLibraryFilters = { limit: 25 };

function ActionButton({
  label,
  onClick,
}: {
  label: string;
  onClick?: () => void;
}) {
  return (
    <button className="forms-library-action" type="button" onClick={onClick}>
      {label}
    </button>
  );
}

function FormCard({
  item,
  onPreview,
  onPrint,
  onDownloadWord,
  onDownloadPdf,
  onAddToIncident,
}: {
  item: FormLibraryItem;
  onPreview?: (item: FormLibraryItem) => void;
  onPrint?: (item: FormLibraryItem) => void;
  onDownloadWord?: (item: FormLibraryItem) => void;
  onDownloadPdf?: (item: FormLibraryItem) => void;
  onAddToIncident?: (item: FormLibraryItem) => void;
}) {
  const physical = item.outputKind === "physical_only";
  return (
    <article className="forms-library-card" aria-label={item.name}>
      <header className="forms-library-card-header">
        <div>
          <p className="forms-library-category">{item.category.replaceAll("_", " ")}</p>
          <h2>{item.name}</h2>
        </div>
        <span className={`forms-library-kind ${physical ? "physical" : "digital"}`}>
          {physical ? "Physical form" : "Digital form"}
        </span>
      </header>
      <p className="forms-library-description">{item.description}</p>
      {item.revisionLabel ? (
        <p className="forms-library-revision">Revision: {item.revisionLabel}</p>
      ) : null}
      {physical ? (
        <div className="forms-library-physical" role="note">
          <strong>PHYSICAL CARBON-COPY FORM REQUIRED</strong>
          <span>{item.obtainFrom ?? "Use the approved department forms location."}</span>
          <span>No digital replacement will be generated.</span>
        </div>
      ) : null}
      <div className="forms-library-actions" aria-label={`${item.name} actions`}>
        {item.actions.preview ? (
          <ActionButton
            label={`Preview ${item.name}`}
            onClick={() => onPreview?.(item)}
          />
        ) : null}
        {item.actions.print ? (
          <ActionButton
            label={`Print ${item.name}`}
            onClick={() => onPrint?.(item)}
          />
        ) : null}
        {item.actions.downloadWord ? (
          <ActionButton
            label={`Download ${item.name} as Word`}
            onClick={() => onDownloadWord?.(item)}
          />
        ) : null}
        {item.actions.downloadPdf ? (
          <ActionButton
            label={`Download ${item.name} as PDF`}
            onClick={() => onDownloadPdf?.(item)}
          />
        ) : null}
        {item.actions.addToIncident ? (
          <ActionButton
            label={`Add ${item.name} to an incident`}
            onClick={() => onAddToIncident?.(item)}
          />
        ) : null}
      </div>
    </article>
  );
}

export function FormsLibraryPage({
  onPreview,
  onPrint,
  onDownloadWord,
  onDownloadPdf,
  onAddToIncident,
}: FormsLibraryPageProps) {
  const [query, setQuery] = useState("");
  const [outputKind, setOutputKind] = useState<FormOutputKind | "">("");
  const [filters, setFilters] = useState<FormsLibraryFilters>(EMPTY_FILTERS);
  const [items, setItems] = useState<FormLibraryItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void fetchFormsLibrary(filters)
      .then((response) => {
        if (!active) return;
        setItems(response.items);
        setNextCursor(response.nextCursor);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setItems([]);
        setNextCursor(null);
        setError(reason instanceof Error ? reason.message : "The Forms Library could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [filters, reloadToken]);

  const submit = useCallback((event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFilters({
      q: query.trim() || undefined,
      outputKind: outputKind || undefined,
      limit: 25,
    });
  }, [outputKind, query]);

  const loadMore = useCallback(() => {
    if (!nextCursor || loading) return;
    const cursor = nextCursor;
    setLoading(true);
    void fetchFormsLibrary({ ...filters, cursor })
      .then((response) => {
        setItems((current) => [...current, ...response.items]);
        setNextCursor(response.nextCursor);
        setError(null);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "More forms could not be loaded.");
      })
      .finally(() => setLoading(false));
  }, [filters, loading, nextCursor]);

  return (
    <section className="forms-library-page" aria-labelledby="forms-library-heading">
      <header className="forms-library-heading">
        <div>
          <p className="forms-library-overline">Officer Utilities</p>
          <h1 id="forms-library-heading">Forms Library</h1>
          <p>Find approved forms quickly. Digital and physical paperwork rules stay visible.</p>
        </div>
      </header>

      <form className="forms-library-filters" role="search" onSubmit={submit}>
        <label>
          <span>Search forms</span>
          <input
            aria-label="Search forms"
            type="search"
            value={query}
            maxLength={200}
            onChange={(event) => setQuery(event.currentTarget.value)}
            placeholder="Form name, code, or category"
          />
        </label>
        <label>
          <span>Form type</span>
          <select
            aria-label="Form type"
            value={outputKind}
            onChange={(event) => setOutputKind(event.currentTarget.value as FormOutputKind | "")}
          >
            <option value="">All approved forms</option>
            <option value="digital_document">Digital forms</option>
            <option value="physical_only">Physical forms</option>
          </select>
        </label>
        <button className="forms-library-search-button" type="submit">Search</button>
      </form>

      {error ? (
        <div className="forms-library-state error" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => setReloadToken((value) => value + 1)}>Try again</button>
        </div>
      ) : null}
      {loading && items.length === 0 ? (
        <div className="forms-library-state" aria-busy="true">Loading approved forms…</div>
      ) : null}
      {!loading && !error && items.length === 0 ? (
        <div className="forms-library-state">No approved forms match these filters.</div>
      ) : null}
      {items.length > 0 ? (
        <div className="forms-library-grid">
          {items.map((item) => (
            <FormCard
              key={item.templateId}
              item={item}
              onPreview={onPreview}
              onPrint={onPrint}
              onDownloadWord={onDownloadWord}
              onDownloadPdf={onDownloadPdf}
              onAddToIncident={onAddToIncident}
            />
          ))}
        </div>
      ) : null}
      {nextCursor ? (
        <button className="forms-library-load-more" type="button" onClick={loadMore} disabled={loading}>
          {loading ? "Loading…" : "Load more forms"}
        </button>
      ) : null}
    </section>
  );
}
