import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SaveState } from "./SaveState";

describe("SaveState", () => {
  it("announces server persistence changes atomically", () => {
    const view = render(<SaveState state="saving" />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status).toHaveAttribute("aria-atomic", "true");
    expect(status).toHaveTextContent("Saving to server…");

    view.rerender(<SaveState state="saved" />);
    expect(status).toHaveTextContent("Saved to server");
  });

  it("does not claim reconnecting work reached the server", () => {
    render(<SaveState state="reconnecting" />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Reconnecting — changes remain visible; server save not confirmed",
    );
  });
});
