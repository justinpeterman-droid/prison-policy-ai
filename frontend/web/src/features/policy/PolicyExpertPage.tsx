import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Field, StatusMessage } from "../../design-system/Primitives";
import { askPolicyQuestion, type PolicyAnswer } from "./api";
import "./policy-expert.css";

export function PolicyExpertPage() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<PolicyAnswer | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setAnswer(null);
    const cleaned = question.trim();
    if (!cleaned) {
      setError("Enter a policy question before submitting.");
      return;
    }
    setSubmitting(true);
    try {
      setAnswer(await askPolicyQuestion(cleaned));
    } catch (reason: unknown) {
      setError(
        reason instanceof Error
          ? reason.message
          : "The Policy Expert could not answer this question.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="policy-page" aria-labelledby="policy-heading">
      <header className="policy-heading">
        <div>
          <p>Officer Utilities</p>
          <h1 id="policy-heading">Policy Expert</h1>
          <span>Ask a policy question and review the cited source material.</span>
        </div>
      </header>

      <section className="policy-question-panel">
        <form onSubmit={submit}>
          <Field label="Policy question" required>
            <textarea
              aria-label="Policy question"
              value={question}
              maxLength={2_000}
              rows={5}
              onChange={(event) => setQuestion(event.currentTarget.value)}
              placeholder="Example: What documentation is required after a use-of-force incident?"
            />
          </Field>
          <div className="policy-form-footer">
            <span>{question.length.toLocaleString()} / 2,000</span>
            <Button variant="primary" type="submit" loading={submitting}>
              {submitting ? "Searching policy…" : "Ask Policy Expert"}
            </Button>
          </div>
        </form>
        <p className="policy-boundary-note">
          A Policy Expert answer does not add or change facts in an incident. Enter confirmed facts separately in the incident workflow.
        </p>
      </section>

      {error ? <StatusMessage className="policy-state error" tone="dependency-unavailable">{error}</StatusMessage> : null}
      {submitting ? (
        <StatusMessage className="policy-state" aria-busy="true">Searching approved policy sources…</StatusMessage>
      ) : null}

      {answer ? (
        <div className="policy-result-grid">
          <section className="policy-answer-panel" aria-label="Policy answer">
            <header>
              <p>Citation-backed response</p>
              <h2>Answer</h2>
            </header>
            <div className="policy-answer-text">{answer.answer}</div>
          </section>

          <section className="policy-sources-panel" aria-label="Policy sources">
            <header>
              <p>Review the authority</p>
              <h2>Sources</h2>
            </header>
            <ol>
              {answer.citations.map((citation, index) => (
                <li key={`${citation.title}-${citation.location ?? index}`}>
                  <strong>{citation.title}</strong>
                  {citation.location ? <span>{citation.location}</span> : null}
                  {citation.excerpt ? <blockquote>{citation.excerpt}</blockquote> : null}
                </li>
              ))}
            </ol>
          </section>
        </div>
      ) : null}
    </section>
  );
}
