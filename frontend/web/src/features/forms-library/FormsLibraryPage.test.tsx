import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FormsLibraryPage } from "./FormsLibraryPage";
import {
  fetchFormsLibrary,
  prepareFormDownload,
  previewFormSelection,
  type FormLibraryItem,
} from "./api";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    fetchFormsLibrary: vi.fn(),
    previewFormSelection: vi.fn(),
    prepareFormDownload: vi.fn(),
  };
});

const mockedFetch = vi.mocked(fetchFormsLibrary);
const mockedPreview = vi.mocked(previewFormSelection);
const mockedDownload = vi.mocked(prepareFormDownload);

const DIGITAL: FormLibraryItem = {
  templateId: "00000000-0000-4000-8000-000000000001",
  code: "medical_documentation_checklist",
  name: "Medical Documentation Checklist",
  category: "medical",
  purpose: "Approved digital medical documentation checklist.",
  whenUsed: "Use when medical evaluation or treatment is documented.",
  outputKind: "digital_document",
  revisionLabel: "Current approved revision",
  capabilities: ["preview", "print", "download_pdf", "fillable", "blank", "attach_to_incident"],
  frequent: true,
  obtainFrom: null,
};

const PHYSICAL: FormLibraryItem = {
  templateId: "00000000-0000-4000-8000-000000000002",
  code: "chain_of_custody_physical",
  name: "Chain of Custody",
  category: "evidence",
  purpose: "Official physical carbon-copy form.",
  whenUsed: "Use when evidence is transferred.",
  outputKind: "physical_only",
  revisionLabel: "Current approved revision",
  capabilities: ["attach_to_incident", "physical_guidance"],
  frequent: true,
  obtainFrom: "Approved forms location",
};

beforeEach(() => {
  mockedFetch.mockResolvedValue({
    requestPath: "/forms?limit=25",
    nextCursor: null,
    categories: ["evidence", "medical"],
    items: [DIGITAL, PHYSICAL],
  });
  mockedPreview.mockResolvedValue({
    items: [DIGITAL, PHYSICAL],
    digitalItems: [DIGITAL],
    physicalItems: [PHYSICAL],
  });
  mockedDownload.mockResolvedValue({
    downloadableItems: [DIGITAL],
    skippedPhysicalItems: [PHYSICAL],
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Forms Library", () => {
  it("shows permitted digital actions and no substitute for physical paperwork", async () => {
    render(<FormsLibraryPage />);

    const digital = await screen.findByRole("article", { name: DIGITAL.name });
    expect(within(digital).getByText(DIGITAL.purpose)).toBeInTheDocument();
    expect(within(digital).getByText(DIGITAL.whenUsed)).toBeInTheDocument();
    expect(within(digital).getByRole("button", { name: `Preview ${DIGITAL.name}` })).toBeInTheDocument();
    expect(within(digital).getByRole("button", { name: `Print ${DIGITAL.name}` })).toBeInTheDocument();
    expect(within(digital).getByRole("button", { name: `Review download options for ${DIGITAL.name}` })).toBeInTheDocument();

    const physical = screen.getByRole("article", { name: PHYSICAL.name });
    expect(within(physical).getByText("PHYSICAL CARBON-COPY FORM REQUIRED")).toBeInTheDocument();
    expect(within(physical).getByText("Approved forms location")).toBeInTheDocument();
    expect(within(physical).queryByRole("button", { name: /Print/i })).not.toBeInTheDocument();
    expect(within(physical).queryByRole("button", { name: /download/i })).not.toBeInTheDocument();
  });

  it("submits bounded search and category filters", async () => {
    render(<FormsLibraryPage />);
    await screen.findByText(DIGITAL.name);

    fireEvent.change(screen.getByRole("searchbox", { name: "Search forms" }), {
      target: { value: "custody" },
    });
    fireEvent.change(screen.getByLabelText("Form category"), {
      target: { value: "evidence" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(mockedFetch).toHaveBeenLastCalledWith(expect.objectContaining({
        q: "custody",
        category: "evidence",
      }));
    });
  });

  it("previews selected forms in order and warns that physical forms are skipped", async () => {
    render(<FormsLibraryPage />);
    await screen.findByText(DIGITAL.name);

    fireEvent.click(screen.getByLabelText(`Select ${DIGITAL.name}`));
    fireEvent.click(screen.getByLabelText(`Select ${PHYSICAL.name}`));
    fireEvent.click(screen.getByRole("button", { name: "Preview selected" }));

    await waitFor(() => {
      expect(mockedPreview).toHaveBeenCalledWith([DIGITAL.templateId, PHYSICAL.templateId]);
    });
    const inspector = screen.getByRole("complementary", { name: "Selected forms review" });
    expect(within(inspector).getAllByRole("listitem")[0]).toHaveTextContent(DIGITAL.name);
    expect(within(inspector).getAllByRole("listitem")[1]).toHaveTextContent(PHYSICAL.name);
    expect(within(inspector).getByText("Physical forms are not included in digital output")).toBeInTheDocument();
  });

  it("renders an honest empty state instead of sample forms", async () => {
    mockedFetch.mockResolvedValueOnce({
      requestPath: "/forms?limit=25",
      nextCursor: null,
      categories: [],
      items: [],
    });
    render(<FormsLibraryPage />);

    expect(await screen.findByText("No approved forms match these filters.")).toBeInTheDocument();
  });
});
