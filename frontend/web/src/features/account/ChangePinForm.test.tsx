import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChangePinForm } from "./ChangePinForm";
import { changePin } from "./api";

vi.mock("./api", () => ({ changePin: vi.fn() }));

const mockedChangePin = vi.mocked(changePin);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Change PIN form", () => {
  it("requires matching new PIN values and clears fields after success", async () => {
    mockedChangePin.mockResolvedValue(undefined);
    const onChanged = vi.fn();
    render(<ChangePinForm onChanged={onChanged} />);

    fireEvent.change(screen.getByLabelText("Current PIN"), { target: { value: "1234" } });
    fireEvent.change(screen.getByLabelText("New PIN"), { target: { value: "5678" } });
    fireEvent.change(screen.getByLabelText("Confirm new PIN"), { target: { value: "5678" } });
    fireEvent.click(screen.getByRole("button", { name: "Change PIN" }));

    await waitFor(() => expect(mockedChangePin).toHaveBeenCalledWith("1234", "5678"));
    expect(await screen.findByRole("status")).toHaveTextContent("PIN changed");
    expect(onChanged).toHaveBeenCalled();
    expect(screen.getByLabelText("Current PIN")).toHaveValue("");
    expect(screen.getByLabelText("New PIN")).toHaveValue("");
  });

  it("does not submit mismatched PINs", async () => {
    render(<ChangePinForm />);
    fireEvent.change(screen.getByLabelText("Current PIN"), { target: { value: "1234" } });
    fireEvent.change(screen.getByLabelText("New PIN"), { target: { value: "5678" } });
    fireEvent.change(screen.getByLabelText("Confirm new PIN"), { target: { value: "8765" } });
    fireEvent.click(screen.getByRole("button", { name: "Change PIN" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("do not match");
    expect(mockedChangePin).not.toHaveBeenCalled();
  });

  it("keeps values visible after a retryable failure", async () => {
    mockedChangePin.mockRejectedValueOnce(new Error("Account service is temporarily unavailable."));
    render(<ChangePinForm />);
    fireEvent.change(screen.getByLabelText("Current PIN"), { target: { value: "1234" } });
    fireEvent.change(screen.getByLabelText("New PIN"), { target: { value: "5678" } });
    fireEvent.change(screen.getByLabelText("Confirm new PIN"), { target: { value: "5678" } });
    fireEvent.click(screen.getByRole("button", { name: "Change PIN" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
    expect(screen.getByLabelText("Current PIN")).toHaveValue("1234");
    expect(screen.getByLabelText("New PIN")).toHaveValue("5678");
  });
});
