import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InterfaceIcon } from "./InterfaceIcon";

describe("InterfaceIcon", () => {
  it("stays out of the accessibility tree when it decorates a named control", () => {
    const { container } = render(<button aria-label="Close"><InterfaceIcon name="close" /></button>);

    expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("can expose an accessible title when the icon conveys information", () => {
    render(<InterfaceIcon name="health" title="System health" />);

    expect(screen.getByRole("img", { name: "System health" })).toBeInTheDocument();
  });
});
