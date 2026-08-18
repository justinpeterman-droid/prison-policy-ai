import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpenText,
  FileSearch,
  Filter,
  MessageSquareText,
  Search,
} from "lucide-react";
import { designPreviewEnabled } from "../api/client";
import { EmptyState, PageHeader, Section } from "../components/ui";
import { previewPolicyDocuments } from "../data/preview";
import type { PolicyDocument } from "../types";

export function PolicyLibraryPage() {
  const [query, setQuery] = useState("");
  const [section, setSection] = useState("All sections");
  const [selectedId, setSelectedId] = useState(previewPolicyDocuments[0]?.id ?? "");

  const sections = useMemo(
    () => ["All sections", ...Array.from(new Set(previewPolicyDocuments.map((document) => document.section)))],
    [],
  );
  const documents = designPreviewEnabled ? previewPolicyDocuments : [];
  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return documents.filter((document) => {
      if (section !== "All sections" && document.section !== section) return false;
      if (!normalized) return true;
      return [document.title, document.code, document.section, document.summary, ...document.tags]
        .some((value) => value.toLowerCase().includes(normalized));
    });
  }, [documents, query, section]);
  const selected = documents.find((document) => document.id === selectedId) ?? filtered[0] ?? null;

  return (
    <div className="page-stack library-page">
      <PageHeader
        eyebrow="Reference workspace"
        title="Policy library"
        description="Browse current policy references, then move into a cited question when you need help applying them."
        actions={<Link className="button button--primary button--md" to="/policy"><MessageSquareText aria-hidden="true" /><span>Ask Policy Expert</span></Link>}
      />

      {!designPreviewEnabled ? (
        <EmptyState
          icon={<FileSearch aria-hidden="true" />}
          title="Document-library connection is not enabled yet"
          description="The design is ready for a server-authorized policy catalog endpoint. Policy Expert remains the supported live citation surface."
          action={<Link className="button button--primary button--md" to="/policy"><MessageSquareText aria-hidden="true" /><span>Open Policy Expert</span></Link>}
        />
      ) : (
        <div className="library-workspace">
          <Section className="library-index">
            <div className="library-toolbar">
              <label className="search-field">
                <Search aria-hidden="true" />
                <span className="sr-only">Search policy library</span>
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search title, number, topic, or keyword" />
              </label>
              <label className="select-control">
                <Filter aria-hidden="true" />
                <span className="sr-only">Filter policy section</span>
                <select value={section} onChange={(event) => setSection(event.target.value)}>
                  {sections.map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
            </div>
            <div className="document-list" role="list">
              {filtered.map((document) => (
                <button
                  key={document.id}
                  className={document.id === selected?.id ? "document-list-item active" : "document-list-item"}
                  onClick={() => setSelectedId(document.id)}
                  role="listitem"
                >
                  <span className="document-list-item__icon"><BookOpenText aria-hidden="true" /></span>
                  <span className="document-list-item__copy">
                    <small>{document.code} · {document.section}</small>
                    <strong>{document.title}</strong>
                    <span>{document.summary}</span>
                  </span>
                  <ArrowRight aria-hidden="true" />
                </button>
              ))}
              {!filtered.length ? (
                <EmptyState icon={<FileSearch aria-hidden="true" />} title="No matching policies" description="Try a broader keyword or choose another section." />
              ) : null}
            </div>
          </Section>

          <article className="document-viewer">
            {selected ? <DocumentViewer document={selected} /> : null}
          </article>
        </div>
      )}
    </div>
  );
}

function DocumentViewer({ document }: { document: PolicyDocument }) {
  return (
    <>
      <header className="document-viewer__header">
        <div>
          <p className="eyebrow">{document.section}</p>
          <h2>{document.title}</h2>
          <p>{document.code} · {document.updatedLabel}</p>
        </div>
        <Link className="button button--secondary button--md" to="/policy"><MessageSquareText aria-hidden="true" /><span>Ask about this policy</span></Link>
      </header>
      <div className="document-viewer__summary"><strong>Purpose</strong><p>{document.summary}</p></div>
      <div className="document-viewer__body">
        <h3>Selected guidance</h3>
        {document.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
      </div>
      <footer className="document-viewer__footer">
        <span>Preview content uses fictional policy language for interface design only.</span>
      </footer>
    </>
  );
}
