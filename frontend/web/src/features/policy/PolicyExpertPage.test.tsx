import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PolicyExpertPage } from "./PolicyExpertPage";
import { askPolicyQuestion } from "./api";

vi.mock("./api", () => ({ askPolicyQuestion: vi.fn() }));

const mockedAsk = vi.mocked(askPolicyQuestion);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Policy Expert", () => {
  it("shows a cited answer and keeps sources separate from the answer", async () => {
    mockedAsk.mockResolvedValueOnce({
      answer: "Fictional policy requires supervisor notification.",
      citations: [
        {
          title: "Fictional Operations Policy",
          location: "Section 2.1 · Page 4",
          excerpt: "Notify the shift supervisor.",
        },
      ],
    });
    render(<PolicyExpertPage />);

    fireEvent.change(screen.getByLabelText("Policy question"), {
      target: { value: "When is supervisor notification required?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask Policy Expert" }));

    const answer = await screen.findByRole("region", { name: "Policy answer" });
    expect(within(answer).getByText("Fictional policy requires supervisor notification.")).toBeInTheDocument();
    const sources = screen.getByRole("region", { name: "Policy sources" });
    expect(within(sources).getByText("Fictional Operations Policy")).toBeInTheDocument();
    expect(within(sources).getByText("Section 2.1 · Page 4")).toBeInTheDocument();
  });

  it("does not submit an empty question", async () => {
    render(<PolicyExpertPage />);
    fireEvent.click(screen.getByRole("button", { name: "Ask Policy Expert" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Enter a policy question");
    expect(mockedAsk).not.toHaveBeenCalled();
  });

  it("preserves the question after a dependency failure", async () => {
    mockedAsk.mockRejectedValueOnce(new Error("Policy search is temporarily unavailable."));
    render(<PolicyExpertPage />);
    const input = screen.getByLabelText("Policy question");
    fireEvent.change(input, { target: { value: "What does fictional policy say?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask Policy Expert" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
    expect(input).toHaveValue("What does fictional policy say?");
  });

  it("explains that policy answers do not change incident facts", () => {
    render(<PolicyExpertPage />);
    expect(screen.getByText(/does not add or change facts in an incident/i)).toBeInTheDocument();
  });
});
