import { describe, expect, it, vi } from "vitest";
import { fetchFormsLibrary, parseFormsLibraryItem } from "./api";

vi.mock("../../api/client", () => ({
  webApiRequest: vi.fn(async (path: string) => ({
    path,
    items: [],
    next_cursor: null,
  })),
}));

describe("Forms Library API", () => {
  it("parses only the sanitized action contract", () => {
    const item = parseFormsLibraryItem({
      template_id: "00000000-0000-4000-8000-000000000001",
      code: "chain_of_custody_physical",
      name: "Chain of Custody",
      category: "incident_forms",
      output_kind: "physical_only",
      revision_label: null,
      description: "Official physical carbon-copy form.",
      obtain_from: "Approved forms location",
      actions: {
        preview: false,
        print: false,
        download_word: false,
        download_pdf: false,
        add_to_incident: true,
        physical_guidance: true,
      },
    });

    expect(item.outputKind).toBe("physical_only");
    expect(item.actions.print).toBe(false);
    expect(item.actions.physicalGuidance).toBe(true);
    expect(JSON.stringify(item)).not.toContain("template_path");
  });

  it("builds bounded encoded filters", async () => {
    const response = await fetchFormsLibrary({
      q: "chain custody",
      category: "incident_forms",
      outputKind: "physical_only",
      limit: 25,
      cursor: "signed cursor",
    });

    expect(response.requestPath).toContain("q=chain+custody");
    expect(response.requestPath).toContain("category=incident_forms");
    expect(response.requestPath).toContain("output_kind=physical_only");
    expect(response.requestPath).toContain("cursor=signed+cursor");
  });
});
