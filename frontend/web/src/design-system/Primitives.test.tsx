import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Button, Field, ListRow, PanelHeader, StatusMessage, Surface, buttonClassName, listRowClassName } from "./Primitives";

describe("shared visual primitives", () => {
  it.each(["primary", "secondary", "destructive", "quiet", "icon", "segment"] as const)(
    "publishes the %s button variant",
    (variant) => expect(buttonClassName(variant)).toBe(`gow-button gow-button--${variant}`),
  );

  it("exposes loading and selected button state without permitting activation", () => {
    render(<Button loading selected>Save</Button>);
    const button = screen.getByRole("button", { name: "Save" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button).toHaveAttribute("aria-pressed", "true");
    expect(button).toHaveAttribute("data-selected", "true");
  });

  it("keeps icon-only controls accessible by contract", () => {
    render(<Button variant="icon" aria-label="Close"><span aria-hidden="true">×</span></Button>);
    expect(screen.getByRole("button", { name: "Close" })).toHaveClass("gow-button--icon");
  });

  it("publishes every shared surface variant", () => {
    const variants = ["action", "information", "list", "inset", "empty", "warning", "dialog"] as const;
    const { container } = render(<>{variants.map((variant) => <Surface key={variant} variant={variant} />)}</>);
    for (const variant of variants) expect(container.querySelector(`.gow-surface--${variant}`)).not.toBeNull();
  });

  it("standardizes panel heading hierarchy and optional action placement", () => {
    render(<PanelHeader eyebrow="Current priority" heading="Continue work" action={<button>Open</button>}>Supporting copy</PanelHeader>);
    expect(screen.getByRole("heading", { name: "Continue work", level: 2 })).toBeInTheDocument();
    expect(screen.getByText("Current priority")).toHaveClass("gow-panel-header__eyebrow");
    expect(screen.getByRole("button", { name: "Open" }).parentElement).toHaveClass("gow-panel-header__action");
  });

  it.each(["navigation", "action"] as const)("publishes the %s list-row pattern", (variant) => {
    const { container } = render(<ListRow variant={variant}>Row</ListRow>);
    expect(container.firstChild).toHaveClass(...listRowClassName(variant).split(" "));
  });

  it("standardizes recoverable and assertive message semantics", () => {
    const { rerender } = render(<StatusMessage tone="success">Saved</StatusMessage>);
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
    rerender(<StatusMessage tone="dependency-unavailable">Service unavailable</StatusMessage>);
    expect(screen.getByRole("alert")).toHaveAttribute("aria-live", "assertive");
  });

  it("keeps a visible label and wires required, hint, and invalid messaging to its control", () => {
    render(<Field label="Employee number" required hint="Use the roster number." error="Check this value."><input /></Field>);
    const input = screen.getByRole("textbox", { name: /Employee number/ });
    expect(input).toHaveClass("gow-control");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Use the roster number. Check this value.");
    expect(screen.getByText(/required/)).toHaveClass("gow-visually-hidden");
  });

  it("uses one required and optional vocabulary", () => {
    render(<><Field label="Required field" requirement="required"><input /></Field><Field label="Optional field" requirement="optional"><input /></Field></>);
    expect(screen.getByText("(required)")).toHaveClass("gow-visually-hidden");
    expect(screen.getByText("(optional)")).toHaveClass("gow-visually-hidden");
  });
});
