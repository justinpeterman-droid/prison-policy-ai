import { apiRequest, requestId } from "../../api/client";
import type { PolicyAnswer, PolicyTurn } from "../../types";

interface RawPolicyAnswer {
  answer: string;
  citations: Array<{ n: number; source: string; text: string }>;
  sources: string[];
  retrieved_sources: string[];
}

export async function askPolicyQuestion(
  question: string,
  history: PolicyTurn[],
): Promise<PolicyAnswer> {
  const raw = await apiRequest<RawPolicyAnswer>("/web-api/policy/questions", {
    method: "POST",
    headers: { "Idempotency-Key": requestId("policy") },
    body: JSON.stringify({
      question,
      history: history.slice(-6).map((turn) => ({
        question: turn.question,
        answer: turn.answer,
      })),
    }),
  });
  return {
    answer: raw.answer,
    citations: raw.citations,
    sources: raw.sources,
    retrievedSources: raw.retrieved_sources,
  };
}
