import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DocumentStudioPage } from "./DocumentStudioPage";

const INCIDENT_ID = "00000000-0000-4000-8000-000000000029";

function ok(data: unknown): Response {
  return new Response(JSON.stringify({ data }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function apiError(status: number, code: string, message: string): Response {
  return new Response(JSON.stringify({
    error: { code, message, retryable: true, details: {} },
  }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const INCIDENT = {
  incident_id: INCIDENT_ID,
  incident_number: "2026-08-029",
  incident_name: "Barracks 4 Fight",
  status: "in_progress",
  current_revision_number: 3,
  reporting_staff_ids: ["00000000-0000-4000-8000-000000000002"],
  reporting_officers: [
    {
      staff_id: "00000000-0000-4000-8000-000000000002",
      display_name: "Officer Casey Morgan",
    },
  ],
  field_notes: "Fictional reviewed incident notes.",
  incident_date: "2026-08-19",
  incident_time: "14:30:00",
  facility: "Fictional Unit",
  shift: "A",
  location: "Barracks 4",
  category: "inmate_fight",
  classification: { category: "inmate_fight" },
  extracted_facts: { inmates_involved: "Fictional inmate TEST-0001" },
  gap_answers: { medical_disposition: "Seen by Infirmary staff" },
  charges: [],
  validation: { facts_reviewed: true },
  warnings: [],
  created_at: "2026-08-19T14:30:00Z",
  updated_at: "2026-08-19T14:50:00Z",
};

const REPORTS = {
  items: [
    {
      report_id: "00000000-0000-4000-8000-000000000101",
      incident_id: INCIDENT_ID,
      report_type: "first_person",
      presentation: "document",
      allowed_actions: ["edit", "preview", "print", "download_word"],
      status: "in_progress",
      current_revision_number: 2,
      reporting_officer: {
        staff_id: "00000000-0000-4000-8000-000000000002",
        display_name: "Officer Casey Morgan",
      },
      preparer: {
        staff_id: "00000000-0000-4000-8000-000000000002",
        display_name: "Officer Casey Morgan",
      },
      updated_at: "2026-08-19T14:50:00Z",
    },
    {
      report_id: "00000000-0000-4000-8000-000000000102",
      incident_id: INCIDENT_ID,
      report_type: "supervisor_summary",
      presentation: "copy_text",
      allowed_actions: ["copy_text", "edit"],
      status: "in_progress",
      current_revision_number: 1,
      reporting_officer: {
        staff_id: "00000000-0000-4000-8000-000000000002",
        display_name: "Officer Casey Morgan",
      },
      preparer: {
        staff_id: "00000000-0000-4000-8000-000000000002",
        display_name: "Officer Casey Morgan",
      },
      updated_at: "2026-08-19T14:49:00Z",
    },
  ],
};

const PACKET = {
  items: [
    {
      packet_item_id: "00000000-0000-4000-8000-000000000201",
      template_code: "medical_documentation_checklist",
      name: "Medical Documentation Checklist",
      output_kind: "digital_document",
      presentation: "document",
      allowed_actions: ["preview", "print"],
      packet_group: "recommended",
      packet_state: "selected",
      selection_reason: "Recommended when medical information is present.",
      not_applicable_reason: null,
      reporting_staff_member_id: null,
      source_incident_revision_number: 3,
      definition: { description: "Review medical documentation." },
      form_instance: {
        form_instance_id: "00000000-0000-4000-8000-000000000301",
        source_incident_revision_number: 3,
        populated_fields: { incident_number: "2026-08-029", location: "Barracks 4" },
        manual_fields: {},
        completeness: { state: "ready", missing_fields: [], review_fields: [] },
        updated_at: "2026-08-19T14:51:00Z",
      },
      physical_acknowledgment: null,
    },
    {
      packet_item_id: "00000000-0000-4000-8000-000000000202",
      template_code: "chain_of_custody_physical",
      name: "Chain of Custody — Physical Carbon-Copy Form",
      output_kind: "physical_only",
      presentation: "physical",
      allowed_actions: [],
      packet_group: "required",
      packet_state: "selected",
      selection_reason: "Required for recovered evidence.",
      not_applicable_reason: null,
      reporting_staff_member_id: null,
      source_incident_revision_number: 3,
      definition: {
        description: "Complete the official carbon-copy form by hand.",
        obtain_from: "Approved forms storage",
      },
      form_instance: null,
      physical_acknowledgment: null,
    },
  ],
};

let reportSaveAttempts = 0;

beforeEach(() => {
  reportSaveAttempts = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith(`/incidents/${INCIDENT_ID}`)) return ok(INCIDENT);
      if (url.endsWith(`/incidents/${INCIDENT_ID}/reports`)) return ok(REPORTS);
      if (url.endsWith(`/incidents/${INCIDENT_ID}/packet`)) return ok(PACKET);
      if (url.includes("/reports/00000000-0000-4000-8000-000000000101")) {
        const detail = {
          ...REPORTS.items[0],
          content: {
            narrative: "Fictional first-person report narrative.",
            editable_fields: {},
            validation: {},
            warnings: [],
          },
        };
        if (init?.method === "PATCH") {
          reportSaveAttempts += 1;
          if (reportSaveAttempts === 1) {
            return apiError(409, "revision_conflict", "The report changed on the server.");
          }
          const body = JSON.parse(String(init.body)) as { content: { narrative: string } };
          return ok({ ...detail, current_revision_number: 3, content: { ...detail.content, narrative: body.content.narrative } });
        }
        return ok(detail);
      }
      if (url.includes("/reports/00000000-0000-4000-8000-000000000102")) {
        return ok({
          ...REPORTS.items[1],
          content: {
            narrative: "Fictional supervisor summary for the external records database.",
            editable_fields: {},
            validation: {},
            warnings: [],
          },
        });
      }
      if (url.includes("/form-instances/00000000-0000-4000-8000-000000000301/preview")) {
        return ok({
          form_instance_id: "00000000-0000-4000-8000-000000000301",
          packet_item_id: "00000000-0000-4000-8000-000000000201",
          incident_id: INCIDENT_ID,
          template_code: "medical_documentation_checklist",
          template_name: "Medical Documentation Checklist",
          render_kind: "browser_form",
          fields: { incident_number: "2026-08-029", location: "Barracks 4" },
          completeness: { state: "ready", missing_fields: [], review_fields: [] },
        });
      }
      if (url.includes("/physical")) {
        return ok({
          packet_item_id: "00000000-0000-4000-8000-000000000202",
          incident_id: INCIDENT_ID,
          template_code: "chain_of_custody_physical",
          name: "Chain of Custody — Physical Carbon-Copy Form",
          warning: "PHYSICAL CARBON-COPY FORM REQUIRED",
          description: "Complete the official carbon-copy form by hand.",
          obtain_from: "Approved forms storage",
          guidance_fields: ["incident_number", "location"],
          guidance_values: { incident_number: "2026-08-029", location: "Barracks 4" },
          source_incident_revision_number: 3,
          acknowledgment: null,
          allowed_actions: ["acknowledge_physical"],
        });
      }
      return ok({});
    }),
  );
  Object.assign(navigator, {
    clipboard: { writeText: vi.fn(async () => undefined) },
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Incident Document Studio", () => {
  function renderStudio() {
    return render(
      <MemoryRouter initialEntries={[`/reports/${INCIDENT_ID}`]}>
        <Routes>
          <Route path="/reports/:incidentId" element={<DocumentStudioPage />} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it("opens one incident workspace with the approved six document areas", async () => {
    renderStudio();

    expect(await screen.findByText("2026-08-029")).toBeInTheDocument();
    expect(screen.getByText("Barracks 4 Fight")).toBeInTheDocument();
    for (const tab of [
      "Overview",
      "Officer Reports",
      "Copy to Records",
      "Required Paperwork",
      "Notes & Facts",
      "History",
    ]) {
      expect(screen.getByRole("tab", { name: tab })).toBeInTheDocument();
    }
  });

  it("keeps supervisor summaries copy-only", async () => {
    renderStudio();
    await screen.findByText("2026-08-029");
    fireEvent.click(screen.getByRole("tab", { name: "Copy to Records" }));

    expect(await screen.findByText(/fictional supervisor summary/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /copy supervisor summary/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /print supervisor summary/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /download supervisor summary/i })).not.toBeInTheDocument();
  });

  it("shows printable populated forms and physical-only guidance separately", async () => {
    renderStudio();
    await screen.findByText("2026-08-029");
    fireEvent.click(screen.getByRole("tab", { name: "Required Paperwork" }));

    expect(screen.getByText("Medical Documentation Checklist")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /preview medical documentation checklist/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /print medical documentation checklist/i })).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: /open physical chain of custody guidance/i,
      }),
    );
    expect(
      await screen.findByText("PHYSICAL CARBON-COPY FORM REQUIRED"),
    ).toBeInTheDocument();
    expect(screen.getByText("Approved forms storage")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /print chain of custody/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /download chain of custody/i })).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /mark physical form completed/i }),
    ).toBeInTheDocument();
  });

  it("keeps report edits visible with truthful conflict recovery guidance", async () => {
    renderStudio();
    await screen.findByText("2026-08-029");
    fireEvent.click(screen.getByRole("tab", { name: "Officer Reports" }));
    fireEvent.click(screen.getByRole("button", { name: /first person.*officer casey morgan/i }));

    const narrative = await screen.findByLabelText("First Person narrative");
    fireEvent.change(narrative, { target: { value: "Fictional revised text remains visible." } });
    expect(screen.getByRole("status")).toHaveTextContent("Unsaved changes — server save pending");

    fireEvent.click(screen.getByRole("button", { name: "Save Report" }));
    expect(await screen.findByText("Save conflict — changes remain visible; server save not confirmed")).toBeInTheDocument();
    expect(narrative).toHaveValue("Fictional revised text remains visible.");

    expect(screen.getByRole("button", { name: "Save Blocked by Conflict" })).toBeDisabled();
    const alert = screen.getByRole("alert");
    expect(alert).toHaveAttribute("aria-live", "assertive");
    expect(alert).toHaveAttribute("aria-atomic", "true");
    expect(alert).toHaveTextContent("The report changed on the server");
    expect(alert).toHaveTextContent("Visible work remains on this device");
    expect(alert).toHaveTextContent("reopen the latest server version");
    expect(narrative).toHaveValue("Fictional revised text remains visible.");
  });
});
