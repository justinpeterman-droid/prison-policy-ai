import { webApiRequest } from "../../api/client";
import { POLICY_ROUTE } from "./route-manifest";

export interface PolicyCitation {
  title: string;
  location: string | null;
  excerpt: string | null;
}

export interface PolicyAnswer {
  answer: string;
  citations: PolicyCitation[];
}

const FORBIDDEN_KEYS = new Set([
  "access_token",
  "renewal_token",
  "csrf_token",
  "pin",
  "pin_hash",
  "field_notes",
  "narrative",
]);
const ALLOWED_ROOT_KEYS = new Set([
  POLICY_ROUTE.answerKey,
  POLICY_ROUTE.citationsKey,
  "confidence",
  "model",
  "request_id",
  "warnings",
]);

function object(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`${label} is invalid.`);
  }
  return value as Record<string, unknown>;
}

function boundedText(
  value: unknown,
  label: string,
  maximum: number,
  allowNull = false,
): string | null {
  if (value === null && allowNull) return null;
  if (typeof value !== "string") throw new Error(`${label} is invalid.`);
  const cleaned = value.trim();
  if (!cleaned || cleaned.length > maximum) throw new Error(`${label} is invalid.`);
  return cleaned;
}

function citationLocation(row: Record<string, unknown>): string | null {
  const values: string[] = [];
  const section = row.section ?? row.heading ?? row.policy_section;
  if (typeof section === "string" && section.trim()) values.push(section.trim());
  const page = row.page ?? row.page_number;
  if (typeof page === "number" && Number.isFinite(page)) values.push(`Page ${page}`);
  if (typeof page === "string" && page.trim()) values.push(`Page ${page.trim()}`);
  return values.length ? values.join(" · ") : null;
}

function parseCitation(value: unknown): PolicyCitation {
  if (typeof value === "string") {
    return {
      title: boundedText(value, "Policy citation", 500) as string,
      location: null,
      excerpt: null,
    };
  }
  const row = object(value, "Policy citation");
  const titleValue = row.title ?? row.source_title ?? row.document ?? row.source;
  const title = boundedText(titleValue, "Citation title", 500) as string;
  const excerptValue = row.excerpt ?? row.quote ?? row.snippet ?? null;
  const excerpt = excerptValue === null
    ? null
    : boundedText(excerptValue, "Citation excerpt", 2_000, true);
  return {
    title,
    location: citationLocation(row),
    excerpt,
  };
}

export function parsePolicyAnswer(value: unknown): PolicyAnswer {
  const row = object(value, "Policy answer");
  for (const key of Object.keys(row)) {
    if (FORBIDDEN_KEYS.has(key.toLowerCase()) || !ALLOWED_ROOT_KEYS.has(key)) {
      throw new Error("The Policy Expert response has an unsupported field.");
    }
  }
  const answer = boundedText(
    row[POLICY_ROUTE.answerKey],
    "Policy answer",
    30_000,
  ) as string;
  const rawCitations = row[POLICY_ROUTE.citationsKey];
  if (!Array.isArray(rawCitations) || rawCitations.length === 0 || rawCitations.length > 50) {
    throw new Error("The Policy Expert answer does not include a valid citation.");
  }
  return {
    answer,
    citations: rawCitations.map(parseCitation),
  };
}

export async function askPolicyQuestion(question: string): Promise<PolicyAnswer> {
  const cleaned = question.trim();
  if (!cleaned || cleaned.length > 2_000) {
    throw new Error("Enter a policy question of 1 through 2,000 characters.");
  }
  const raw = await webApiRequest<unknown>(`/policy${POLICY_ROUTE.path}`, {
    method: POLICY_ROUTE.method,
    body: JSON.stringify({ [POLICY_ROUTE.questionField]: cleaned }),
  });
  return parsePolicyAnswer(raw);
}
