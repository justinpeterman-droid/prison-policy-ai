import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WeeklyPaperworkTab } from "./WeeklyPaperworkTab";

describe("WeeklyPaperworkTab", () => {
  it("shows the approved empty state without inventing form cards", () => {
    render(<WeeklyPaperworkTab />);

    expect(screen.getByRole("heading", { name: "Weekly Paperwork Library" })).toBeInTheDocument();
    expect(screen.getByText("No weekly forms have been published.")).toBeInTheDocument();
    expect(screen.getByText(/appear here after approved publication/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /preview/i })).not.toBeInTheDocument();
  });
});
