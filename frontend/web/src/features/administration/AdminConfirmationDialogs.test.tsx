import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AdminElevationDialog } from "./AdminElevationDialog";
import { AdminStepUpDialog } from "./AdminStepUpDialog";

describe("administrator confirmation feedback", () => {
  it.each([
    [
      "workspace elevation",
      <AdminElevationDialog key="elevation" onSubmit={vi.fn()} error="Administrator PIN was not accepted." />,
      "Administrator PIN was not accepted.",
    ],
    [
      "step-up action",
      <AdminStepUpDialog
        key="step-up"
        title="Confirm staff changes"
        description="Save attributed staff corrections."
        error="Staff changes could not be saved."
        onCancel={vi.fn()}
        onConfirm={vi.fn()}
      />,
      "Staff changes could not be saved.",
    ],
  ])("announces the %s error through the shared unstyled destructive contract", (_name, dialog, message) => {
    render(dialog);

    const alert = screen.getByRole("alert");
    expect(alert.tagName).toBe("P");
    expect(alert.className).toBe("admin-form-error");
    expect(alert).toHaveTextContent(message);
    expect(alert).toHaveAttribute("aria-live", "assertive");
    expect(alert).toHaveAttribute("aria-atomic", "true");
  });
});
