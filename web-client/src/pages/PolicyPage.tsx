import { useMemo, useRef, useState } from "react";
import {
  ArrowUp,
  BookOpenCheck,
  Bookmark,
  BookmarkCheck,
  FileText,
  MessageSquareText,
  Plus,
  Quote,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { ApiError, designPreviewEnabled } from "../api/client";
import { Button, EmptyState, Notice, PageHeader, Section } from "../components/ui";
import { askPolicyQuestion } from "../features/policy/policyApi";
import type { PolicyCitation, PolicyTurn } from "../types";
import { useWorkspaceMemory } from "../workspace/WorkspaceMemoryProvider";

const suggestedQuestions = [
  "What must be documented when suspected contraband is found?",
  "When is a separate witness report required after use of force?",
  "What information belongs in an emergency medical response report?",
];

const previewAnswer = {
  answer:
    "When suspected contraband is discovered, staff should control the immediate area, limit handling, document the exact location and surrounding circumstances, identify who was present, notify the appropriate supervisor, and preserve each transfer of custody. The report should distinguish direct observations from statements made by others and should reference the evidence or property receipt when available.",
  citations: [
    {
      n: 1,
      source: "SEC-3.07 · Contraband Control and Evidence Handling",
      text: "Staff discovering suspected contraband must control the immediate area and avoid unnecessary handling. The discovering employee records where the item was found, who was present, and each transfer of custody.",
    },
    {
      n: 2,
      source: "OP-5.14 · Incident Reporting and Documentation",
      text: "Reports must identify the date, approximate time, location, involved persons, actions taken, notifications made, and disposition of evidence when applicable.",
    },
  ],
};

export function PolicyPage() {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<PolicyTurn[]>([]);
  const [selectedCitation, setSelectedCitation] = useState<PolicyCitation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuestion, setLastQuestion] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { savedCitations, saveCitation, removeCitation } = useWorkspaceMemory();

  const submit = async (override?: string) => {
    const normalized = (override ?? question).trim();
    if (!normalized || busy) return;
    setBusy(true);
    setError(null);
    setLastQuestion(normalized);
    setQuestion("");
    try {
      const result = designPreviewEnabled
        ? await new Promise<typeof previewAnswer>((resolve) => window.setTimeout(() => resolve(previewAnswer), 650))
        : await askPolicyQuestion(normalized, turns);
      const turn: PolicyTurn = {
        id: crypto.randomUUID(),
        question: normalized,
        answer: result.answer,
        citations: result.citations,
        createdAt: new Date().toISOString(),
      };
      setTurns((current) => [...current, turn]);
      setSelectedCitation(result.citations[0] ?? null);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The Policy Expert is temporarily unavailable.");
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  };

  const startNew = () => {
    setTurns([]);
    setSelectedCitation(null);
    setError(null);
    setLastQuestion("");
    setQuestion("");
    inputRef.current?.focus();
  };

  const selectedSaved = useMemo(
    () => selectedCitation ? savedCitations.some((item) => item.source === selectedCitation.source && item.n === selectedCitation.n) : false,
    [selectedCitation, savedCitations],
  );

  return (
    <div className="page-stack policy-page">
      <PageHeader
        eyebrow="Cited guidance"
        title="Policy Expert"
        description="Ask a policy question and review the exact source passages used to support the answer."
        actions={<Button variant="secondary" onClick={startNew} icon={<Plus aria-hidden="true" />}>New conversation</Button>}
      />

      <Notice tone="info">
        Policy answers support your review; they are not a substitute for the controlling manual, supervisory direction, or your professional judgment.
      </Notice>

      <div className="policy-workspace">
        <section className="conversation-panel" aria-label="Policy conversation">
          <div className="conversation-panel__header">
            <div><MessageSquareText aria-hidden="true" /><span><strong>Policy conversation</strong><small>Session only · cleared when you sign out</small></span></div>
            {turns.length ? <span className="conversation-count">{turns.length} answer{turns.length === 1 ? "" : "s"}</span> : null}
          </div>

          <div className="conversation-body" aria-live="polite">
            {!turns.length && !busy ? (
              <div className="policy-welcome">
                <div className="policy-welcome__mark"><BookOpenCheck aria-hidden="true" /></div>
                <h2>What policy question can I help you review?</h2>
                <p>Be specific about the task or report requirement. Do not include unnecessary personal or medical details.</p>
                <div className="suggestion-list">
                  {suggestedQuestions.map((suggestion) => (
                    <button key={suggestion} onClick={() => void submit(suggestion)}>
                      <span>{suggestion}</span><ArrowUp aria-hidden="true" />
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {turns.map((turn) => (
              <article className="conversation-turn" key={turn.id}>
                <div className="conversation-message conversation-message--user">
                  <span className="avatar avatar--small" aria-hidden="true">Y</span>
                  <div><p className="message-label">You asked</p><p>{turn.question}</p></div>
                </div>
                <div className="conversation-message conversation-message--assistant">
                  <span className="assistant-mark" aria-hidden="true"><ShieldCheck /></span>
                  <div className="assistant-answer">
                    <div className="assistant-answer__label"><span>Policy Expert</span><small>Grounded in retrieved policy passages</small></div>
                    <p>{turn.answer}</p>
                    <div className="citation-chip-row" aria-label="Answer citations">
                      {turn.citations.map((citation) => (
                        <button
                          key={`${turn.id}-${citation.n}`}
                          className={selectedCitation?.source === citation.source && selectedCitation.n === citation.n ? "citation-chip active" : "citation-chip"}
                          onClick={() => setSelectedCitation(citation)}
                        >
                          <FileText aria-hidden="true" />[{citation.n}] {citation.source.split("·")[0].trim()}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </article>
            ))}

            {busy ? (
              <div className="policy-thinking" role="status">
                <span className="assistant-mark" aria-hidden="true"><Sparkles /></span>
                <div><strong>Reviewing policy sources</strong><span><i /><i /><i /></span></div>
              </div>
            ) : null}

            {error ? (
              <EmptyState
                icon={<RefreshCw aria-hidden="true" />}
                title="The Policy Expert is unavailable"
                description={error}
                action={<Button variant="secondary" onClick={() => void submit(lastQuestion)} disabled={!lastQuestion} icon={<RefreshCw aria-hidden="true" />}>Try again</Button>}
              />
            ) : null}
          </div>

          <form className="policy-composer" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
            <label>
              <span className="sr-only">Policy question</span>
              <textarea
                ref={inputRef}
                value={question}
                onChange={(event) => setQuestion(event.target.value.slice(0, 4000))}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void submit();
                  }
                }}
                placeholder="Ask about a policy, procedure, or report requirement…"
                rows={3}
              />
            </label>
            <div className="policy-composer__footer">
              <span>{question.length.toLocaleString()} / 4,000 · Enter to send, Shift+Enter for a new line</span>
              <Button type="submit" disabled={!question.trim() || busy} icon={<ArrowUp aria-hidden="true" />}>Ask</Button>
            </div>
          </form>
        </section>

        <aside className="citation-panel" aria-label="Citation inspector">
          <div className="citation-panel__header">
            <div><Quote aria-hidden="true" /><span><strong>Source passage</strong><small>Review the policy text supporting the selected answer.</small></span></div>
          </div>
          {selectedCitation ? (
            <div className="citation-detail">
              <div className="citation-detail__source"><span>[{selectedCitation.n}]</span><div><strong>{selectedCitation.source}</strong><small>Retrieved policy passage</small></div></div>
              <blockquote>{selectedCitation.text}</blockquote>
              <Button
                variant={selectedSaved ? "secondary" : "primary"}
                onClick={() => selectedSaved ? removeCitation(selectedCitation.source, selectedCitation.n) : saveCitation(selectedCitation)}
                icon={selectedSaved ? <BookmarkCheck aria-hidden="true" /> : <Bookmark aria-hidden="true" />}
              >
                {selectedSaved ? "Saved for this session" : "Save for this session"}
              </Button>
              <div className="citation-integrity"><ShieldCheck aria-hidden="true" /><span>This passage is displayed exactly as returned by the server citation response.</span></div>
            </div>
          ) : (
            <EmptyState
              icon={<Quote aria-hidden="true" />}
              title="Select a citation"
              description="Ask a question, then choose a numbered source to inspect the supporting passage."
            />
          )}
          <Section title="Source use" className="citation-guidance">
            <ul>
              <li>Read the cited passage in context.</li>
              <li>Confirm the policy is current for your facility.</li>
              <li>Follow supervisory direction when procedures conflict.</li>
            </ul>
          </Section>
        </aside>
      </div>
    </div>
  );
}
