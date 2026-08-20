import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { AdminStaffMember } from "../../api";
import { StaffPicker } from "./StaffPicker";


const STAFF: AdminStaffMember[] = [
  {
    staffId: "00000000-0000-4000-8000-000000000201",
    employeeNumber: "F1001",
    displayName: "Officer Avery Cole",
    rank: "Officer",
    shift: "D",
    isActive: true,
    account: null,
  },
  {
    staffId: "00000000-0000-4000-8000-000000000202",
    employeeNumber: "F1002",
    displayName: "Former Officer",
    rank: null,
    shift: null,
    isActive: false,
    account: null,
  },
];


describe("roster staff picker", () => {
  it("searches active staff and supports keyboard selection, clear, and NOA", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const searchStaff = vi.fn().mockResolvedValue(STAFF);
    const { rerender } = render(
      <StaffPicker
        label="Bks 8 initial officer"
        value={null}
        state="unassigned"
        onChange={onChange}
        searchStaff={searchStaff}
      />,
    );

    const picker = screen.getByRole("combobox", { name: "Bks 8 initial officer" });
    await user.type(picker, "Avery");
    await waitFor(() => expect(searchStaff).toHaveBeenLastCalledWith("Avery"));
    expect(screen.queryByText("Former Officer")).not.toBeInTheDocument();
    await user.keyboard("{ArrowDown}{Enter}");

    expect(onChange).toHaveBeenLastCalledWith({
      staff_id: STAFF[0].staffId,
      display_name_snapshot: "Officer Avery Cole",
    }, "assigned");

    rerender(
      <StaffPicker
        label="Bks 8 initial officer"
        value={{ staff_id: STAFF[0].staffId, display_name_snapshot: STAFF[0].displayName }}
        state="assigned"
        onChange={onChange}
        searchStaff={searchStaff}
      />,
    );
    await user.clear(screen.getByRole("combobox", { name: "Bks 8 initial officer" }));
    expect(onChange).toHaveBeenLastCalledWith(null, "unassigned");

    await user.click(screen.getByRole("combobox", { name: "Bks 8 initial officer" }));
    await user.click(await screen.findByRole("option", { name: /No Officer Available/i }));
    expect(onChange).toHaveBeenLastCalledWith(null, "no_officer_available");
  });
});
