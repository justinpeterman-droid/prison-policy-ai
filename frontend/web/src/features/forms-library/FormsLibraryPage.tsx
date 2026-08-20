import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { InterfaceIcon } from "../../components/InterfaceIcon";
import {
  fetchFormsLibrary,
  prepareFormDownload,
  previewFormSelection,
  type FormDownloadPlan,
  type FormLibraryItem,
  type FormSelectionPlan,
  type FormsLibraryFilters,
} from "./api";
import "./forms-library.css";

interface FormsLibraryPageProps {
  onAddToIncident?: (item: FormLibraryItem) => void;
}

const EMPTY_FILTERS: FormsLibraryFilters = { limit: 25 };

function displayCategory(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function has(item: FormLibraryItem, capability: FormLibraryItem["capabilities"][number]): boolean {
  return item.capabilities.includes(capability);
}

function FormCard({
  item,
  selected,
  busy,
  onToggle,
  onPreview,
  onPrint,
  onDownload,
  onAddToIncident,
}: {
  item: FormLibraryItem;
  selected: boolean;
  busy: boolean;
  onToggle: () => void;
  onPreview: () => void;
  onPrint: () => void;
  onDownload: () => void;
  onAddToIncident?: () => void;
}) {
  const physical = item.outputKind === "physical_only";
  return (
    <article
      className={`forms-library-card ${item.frequent ? "frequent" : ""}`.trim()}
      aria-label={item.name}
    >
      <header className="forms-library-card-header">
        <div>
          <p className="forms-library-category">
            {item.frequent ? "Frequently used · " : ""}{displayCategory(item.category)}
          </p>
          <h2>{item.name}</h2>
        </div>
        <span className={`forms-library-kind ${physical ? "physical" : "digital"}`}>
          {physical ? "Physical form" : "Digital form"}
        </span>
      </header>

      <label className="forms-library-select">
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          aria-label={`Select ${item.name}`}
        />
        <span>Add to selected forms</span>
      </label>

      <div className="forms-library-guidance">
        <p><strong>Purpose</strong>{item.purpose}</p>
        <p><strong>When used</strong>{item.whenUsed}</p>
      </div>
      <p className="forms-library-revision">Revision: {item.revisionLabel}</p>

      {physical ? (
        <div className="forms-library-physical" role="note">
          <strong>PHYSICAL CARBON-COPY FORM REQUIRED</strong>
          <span>{item.obtainFrom ?? "Use the approved department forms location."}</span>
          <span>No digital replacement will be generated.</span>
        </div>
      ) : null}

      <div className="forms-library-actions" aria-label={`${item.name} actions`}>
        {has(item, "preview") ? (
          <button
            className="forms-library-action"
            type="button"
            disabled={busy}
            onClick={onPreview}
            aria-label={`Preview ${item.name}`}
          >
            Preview
          </button>
        ) : null}
        {has(item, "print") ? (
          <button
            className="forms-library-action"
            type="button"
            disabled={busy}
            onClick={onPrint}
            aria-label={`Print ${item.name}`}
          >
            Print
          </button>
        ) : null}
        {has(item, "download_word") || has(item, "download_pdf") ? (
          <button
            className="forms-library-action"
            type="button"
            disabled={busy}
            onClick={onDownload}
            aria-label={`Review download options for ${item.name}`}
          >
            Review download
          </button>
        ) : null}
        {onAddToIncident && has(item, "attach_to_incident") ? (
          <button
            className="forms-library-action"
            type="button"
            disabled={busy}
            onClick={onAddToIncident}
            aria-label={`Add ${item.name} to an incident`}
          >
            Add to incident
          </button>
        ) : null}
      </div>
    </article>
  );
}

function SelectionInspector({
  preview,
  download,
  onClose,
}: {
  preview: FormSelectionPlan | null;
  download: FormDownloadPlan | null;
  onClose: () => void;
}) {
  if (!preview && !download) return null;
  const items = preview?.items ?? [
    ...(download?.downloadableItems ?? []),
    ...(download?.skippedPhysicalItems ?? []),
  ];
  const physical = preview?.physicalItems ?? download?.skippedPhysicalItems ?? [];
  return (
    <aside className="forms-library-inspector" aria-label="Selected forms review">
      <header>
        <div>
          <p>Selected packet</p>
          <h2>{preview ? "Preview selected forms" : "Review download options"}</h2>
        </div>
        <button type="button" aria-label="Close selected forms review" title="Close selected forms review" onClick={onClose}><InterfaceIcon name="close" /></button>
      </header>
      <ol>
        {items.map((item) => (
          <li key={item.templateId}>
            <strong>{item.name}</strong>
            <span>{item.outputKind === "physical_only" ? "Physical guidance" : item.revisionLabel}</span>
          </li>
        ))}
      </ol>
      {physical.length ? (
        <div className="forms-library-physical" role="note">
          <strong>Physical forms are not included in digital output</strong>
          <span>{physical.map((item) => item.name).join(", ")}</span>
          <span>Use the approved physical form location shown on each form.</span>
        </div>
      ) : null}
      {download?.downloadableItems.length ? (
        <p className="forms-library-download-note" role="status">
          {download.downloadableItems.length} digital form{download.downloadableItems.length === 1 ? " is" : "s are"} eligible for supported download formats.
        </p>
      ) : null}
    </aside>
  );
}

export function FormsLibraryPage({ onAddToIncident }: FormsLibraryPageProps) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [filters, setFilters] = useState<FormsLibraryFilters>(EMPTY_FILTERS);
  const [items, setItems] = useState<FormLibraryItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [preview, setPreview] = useState<FormSelectionPlan | null>(null);
  const [download, setDownload] = useState<FormDownloadPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
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
        setCategories(response.categories);
        setNextCursor(response.nextCursor);
        setSelected(new Set());
        setPreview(null);
        setDownload(null);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setItems([]);
        setCategories([]);
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

  const selectedIds = useMemo(() => [...selected], [selected]);

  const submit = useCallback((event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFilters({
      q: query.trim() || undefined,
      category: category || undefined,
      limit: 25,
    });
  }, [category, query]);

  const toggle = useCallback((templateId: string) => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(templateId)) next.delete(templateId);
      else next.add(templateId);
      return next;
    });
    setPreview(null);
    setDownload(null);
  }, []);

  const runPreview = useCallback(async (ids: string[], printAfter = false) => {
    setBusy(true);
    setError(null);
    try {
      const plan = await previewFormSelection(ids);
      setPreview(plan);
      setDownload(null);
      if (printAfter) window.setTimeout(() => window.print(), 50);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "The selected forms could not be previewed.");
    } finally {
      setBusy(false);
    }
  }, []);

  const runDownload = useCallback(async (ids: string[]) => {
    setBusy(true);
    setError(null);
    try {
      setDownload(await prepareFormDownload(ids));
      setPreview(null);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Download options could not be prepared.");
    } finally {
      setBusy(false);
    }
  }, []);

  const loadMore = useCallback(() => {
    if (!nextCursor || loading) return;
    const cursor = nextCursor;
    setLoading(true);
    void fetchFormsLibrary({ ...filters, cursor })
      .then((response) => {
        setItems((current) => [...current, ...response.items]);
        setCategories((current) => [...new Set([...current, ...response.categories])].sort());
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
          <p>Find approved forms quickly. Digital capabilities and physical-paperwork rules remain visible before any action.</p>
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
            placeholder="Form name, code, purpose, or use"
          />
        </label>
        <label>
          <span>Category</span>
          <select
            aria-label="Form category"
            value={category}
            onChange={(event) => setCategory(event.currentTarget.value)}
          >
            <option value="">All approved categories</option>
            {categories.map((item) => (
              <option key={item} value={item}>{displayCategory(item)}</option>
            ))}
          </select>
        </label>
        <button className="forms-library-search-button" type="submit">Search</button>
      </form>

      {selectedIds.length ? (
        <div className="forms-library-selection-bar" role="region" aria-label="Selected forms">
          <strong>{selectedIds.length} selected</strong>
          <button type="button" disabled={busy} onClick={() => void runPreview(selectedIds)}>
            Preview selected
          </button>
          <button type="button" disabled={busy} onClick={() => void runDownload(selectedIds)}>
            Review downloads
          </button>
          <button type="button" disabled={busy} onClick={() => setSelected(new Set())}>
            Clear selection
          </button>
        </div>
      ) : null}

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
        <div className="forms-library-workspace">
          <div className="forms-library-grid">
            {items.map((item) => (
              <FormCard
                key={item.templateId}
                item={item}
                selected={selected.has(item.templateId)}
                busy={busy}
                onToggle={() => toggle(item.templateId)}
                onPreview={() => void runPreview([item.templateId])}
                onPrint={() => void runPreview([item.templateId], true)}
                onDownload={() => void runDownload([item.templateId])}
                onAddToIncident={(
                  onAddToIncident && has(item, "attach_to_incident")
                    ? () => onAddToIncident(item)
                    : undefined
                )}
              />
            ))}
          </div>
          <SelectionInspector
            preview={preview}
            download={download}
            onClose={() => { setPreview(null); setDownload(null); }}
          />
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
