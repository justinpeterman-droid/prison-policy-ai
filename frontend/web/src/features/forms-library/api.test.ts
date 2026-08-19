import { describe, expect, it, vi } from "vitest";
import {
  fetchFormsLibrary,
  parseFormsLibraryItem,
  previewFormSelection,
} from "./api";

const request = vi.fn(async (path: string) => {
  if (path === "/forms/selection/preview") {
    const detail = {
      template_id: "00000000-0000-4000-8000-000000000001",
      code: "chain_of_custody_physical",
      name: "Chain of Custody",
      category: "evidence",
      purpose: "Official physical carbon-copy form.",
      when_used: "Use when evidence is transferred.",
      output_kind: "physical_only",
      revision_label: "Current approved revision",
      capabilities: ["attach_to_incident", "physical_guidance"],
      frequent: true,
      obtain_from: "Approved forms location",
      definition: { obtain_from: "Approved forms location" },
    };
    return { items: [detail], digital_items: [], physical_items: [detail] };
  }
  return {
    items: [],
    categories: ["evidence", "medical"],
    next_cursor: null,
  };
});

vi.mock("../../api/client", () => ({
  webApiRequest: (path: string, init?: RequestInit) => request(path, init),
}));

describe("Forms Library API", () => {
  it("parses only the sanitized capability contract", () => {
    const item = parseFormsLibraryItem({
      template_id: "00000000-0000-4000-8000-000000000001",
      code: "chain_of_custody_physical",
      name: "Chain of Custody",
      category: "evidence",
      purpose: "Official physical carbon-copy form.",
      when_used: "Use when evidence is transferred.",
      output_kind: "physical_only",
      revision_label: "Current approved revision",
      capabilities: ["attach_to_incident", "physical_guidance"],
      frequent: true,
      obtain_from: "Approved forms location",
    });

    expect(item.outputKind).toBe("physical_only");
    expect(item.capabilities).toContain("physical_guidance");
    expect(item.capabilities).not.toContain("print");
    expect(JSON.stringify(item)).not.toContain("template_path");
  });

  it("builds bounded encoded search and category filters", async () => {
    const response = await fetchFormsLibrary({
      q: "chain custody",
      category: "evidence",
      limit: 25,
      cursor: "signed cursor",
    });

    expect(response.requestPath).toContain("q=chain+custody");
    expect(response.requestPath).toContain("category=evidence");
    expect(response.requestPath).toContain("cursor=signed+cursor");
    expect(response.categories).toEqual(["evidence", "medical"]);
  });

  it("keeps physical forms in preview while excluding them from digital output", async () => {
    const plan = await previewFormSelection([
      "00000000-0000-4000-8000-000000000001",
    ]);

    expect(plan.items).toHaveLength(1);
    expect(plan.digitalItems).toHaveLength(0);
    expect(plan.physicalItems[0]?.name).toBe("Chain of Custody");
  });
});
