import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { StaffProfileEditor } from "./StaffProfileEditor";
import * as accountApi from "./api";

vi.mock("./api", () => ({ updateStaffProfile: vi.fn() }));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("administrator staff profile editor", () => {
  it("requires step-up confirmation before correcting roster identity fields", () => {
    render(
      <StaffProfileEditor
        staff={{
          staffId: "staff-1",
          employeeNumber: "F-1001",
          displayName: "Officer Casey Morgan",
          rank: "Officer",
          shift: "A",
          isActive: true,
          account: null,
        }}
        onSaved={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Edit staff profile" }));
    fireEvent.change(screen.getByLabelText("Shift"), { target: { value: "B" } });
    fireEvent.click(screen.getByRole("button", { name: "Save staff changes" }));

    expect(screen.getByRole("heading", { name: "Confirm staff changes" })).toBeInTheDocument();
    expect(accountApi.updateStaffProfile).not.toHaveBeenCalled();
  });
});
