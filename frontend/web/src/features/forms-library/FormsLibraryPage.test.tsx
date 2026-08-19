import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FormsLibraryPage } from "./FormsLibraryPage";
import { fetchFormsLibrary } from "./api";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return { ...actual, fetchFormsLibrary: vi.fn() };
});

const mockedFetch = vi.mocked(fetchFormsLibrary);

beforeEach(() => {
  mockedFetch.mockResolvedValue({
    requestPath: "/forms-library?limit=25",
    nextCursor: null,
    items: [
      {
        templateId: "00000000-0000-4000-8000-000000000001",
        code: "form_005_409",
        name: "005/409 Incident Report",
        category: "incident_forms",
        outputKind: "digital_document",
        revisionLabel: "Current",
        description: "Approved digital incident report.",
        obtainFrom: null,
        actions: {
          preview: true,
          print: true,
          downloadWord: true,
          downloadPdf: false,
          addToIncident: true,
          physicalGuidance: false,
        },
      },
      {
        templateId: "00000000-0000-4000-8000-000000000002",
        code: "chain_of_custody_physical",
        name: "Chain of Custody",
        category: "incident_forms",
        outputKind: "physical_only",
        revisionLabel: null,
        description: "Official physical carbon-copy form.",
        obtainFrom: "Approved forms location",
        actions: {
          preview: false,
          print: false,
          downloadWord: false,
          downloadPdf: false,
          addToIncident: true,
          physicalGuidance: true,
        },
      },
    ],
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Forms Library", () => {
  it("shows permitted digital actions and no substitute for physical paperwork", async () => {
    render(<FormsLibraryPage />);

    const digital = await screen.findByRole("article", { name: "005/409 Incident Report" });
    expect(within(digital).getByRole("button", { name: "Preview 005/409 Incident Report" })).toBeInTheDocument();
    expect(within(digital).getByRole("button", { name: "Print 005/409 Incident Report" })).toBeInTheDocument();
    expect(within(digital).getByRole("button", { name: "Download 005/409 Incident Report as Word" })).toBeInTheDocument();

    const physical = screen.getByRole("article", { name: "Chain of Custody" });
    expect(within(physical).getByText("PHYSICAL CARBON-COPY FORM REQUIRED")).toBeInTheDocument();
    expect(within(physical).getByText("Approved forms location")).toBeInTheDocument();
    expect(within(physical).queryByRole("button", { name: /Print/i })).not.toBeInTheDocument();
    expect(within(physical).queryByRole("button", { name: /Download/i })).not.toBeInTheDocument();
  });

  it("submits bounded search and output filters", async () => {
    render(<FormsLibraryPage />);
    await screen.findByText("005/409 Incident Report");

    fireEvent.change(screen.getByRole("searchbox", { name: "Search forms" }), {
      target: { value: "custody" },
    });
    fireEvent.change(screen.getByLabelText("Form type"), {
      target: { value: "physical_only" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(mockedFetch).toHaveBeenLastCalledWith(expect.objectContaining({
        q: "custody",
        outputKind: "physical_only",
      }));
    });
  });

  it("renders an honest empty state instead of sample forms", async () => {
    mockedFetch.mockResolvedValueOnce({
      requestPath: "/forms-library?limit=25",
      nextCursor: null,
      items: [],
    });
    render(<FormsLibraryPage />);

    expect(await screen.findByText("No approved forms match these filters.")).toBeInTheDocument();
  });
});
