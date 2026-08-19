import { describe, expect, it, vi } from "vitest";
import { askPolicyQuestion, parsePolicyAnswer } from "./api";

const request = vi.fn(async () => ({
  answer: "Fictional policy answer.",
  citations: [{ title: "Fictional Policy", section: "2.1", page: 4 }],
}));

vi.mock("../../api/client", () => ({
  webApiRequest: (...args: unknown[]) => request(...args),
}));

vi.mock("./route-manifest", () => ({
  POLICY_ROUTE: {
    method: "POST",
    path: "/questions",
    questionField: "question",
    answerKey: "answer",
    citationsKey: "citations",
  },
}));

describe("Policy Expert API", () => {
  it("builds the server-owned question field and parses cited answers", async () => {
    const answer = await askPolicyQuestion("What does fictional policy require?");

    expect(request).toHaveBeenCalledWith("/policy/questions", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ question: "What does fictional policy require?" }),
    }));
    expect(answer.answer).toBe("Fictional policy answer.");
    expect(answer.citations[0]?.title).toBe("Fictional Policy");
    expect(answer.citations[0]?.location).toContain("2.1");
  });

  it("accepts bounded string citations but rejects uncited responses", () => {
    expect(parsePolicyAnswer({
      answer: "Fictional answer.",
      citations: ["Fictional Policy § 3"],
    }).citations[0]?.title).toBe("Fictional Policy § 3");

    expect(() => parsePolicyAnswer({
      answer: "Unsupported answer.",
      citations: [],
    })).toThrow(/citation/i);
  });

  it("rejects credential-like or incident-content fields", () => {
    expect(() => parsePolicyAnswer({
      answer: "Fictional answer.",
      citations: ["Fictional Policy"],
      access_token: "forbidden",
    })).toThrow(/unsupported/i);
    expect(() => parsePolicyAnswer({
      answer: "Fictional answer.",
      citations: ["Fictional Policy"],
      field_notes: "forbidden",
    })).toThrow(/unsupported/i);
  });
});
