import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PrintPacket } from "./PrintPacket";

describe("PrintPacket", () => {
  it("preserves the supplied document order", () => {
    render(<PrintPacket><article>First form</article><article>Second form</article></PrintPacket>);
    expect(screen.getByLabelText("Monthly paperwork packet").textContent).toBe("First formSecond form");
  });
});
