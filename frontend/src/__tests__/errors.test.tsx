import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { ResultStep } from "../steps/ResultStep";
import { mockBackend } from "../test-utils";

afterEach(() => vi.unstubAllGlobals());

const noop = () => {};

describe("error states", () => {
  it.each([
    [0, "We could not reach the checker", true],
    [400, "We could not read this chat", false],
    [413, "This chat is too large", false],
    [415, "This file type is not supported", false],
    [422, "Some details are missing", false],
    [500, "Something went wrong", true],
    [504, "The check took too long", true],
  ])("status %i shows its own message", (status, title, canRetry) => {
    render(
      <ResultStep
        outcome={{ state: "error", status, detail: "" }}
        onCancel={noop}
        onBack={noop}
        onRetry={noop}
        onRestart={noop}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(title);
    expect(screen.getByRole("button", { name: "Back" })).toBeInTheDocument();
    expect(!!screen.queryByRole("button", { name: "Try again" })).toBe(canRetry);
  });

  it("uses the backend's message when there is one", () => {
    render(
      <ResultStep
        outcome={{ state: "error", status: 413, detail: "This chat has more than 2,000 messages." }}
        onCancel={noop}
        onBack={noop}
        onRetry={noop}
        onRestart={noop}
      />,
    );
    expect(screen.getByText("This chat has more than 2,000 messages.")).toBeInTheDocument();
  });

  async function analyse() {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("tab", { name: /paste text/i }));
    await user.type(screen.getByLabelText("Chat text"), "hello");
    await user.click(screen.getByRole("button", { name: /next step/i }));
    await user.click(screen.getByRole("button", { name: "Analyse" }));
    return user;
  }

  it("shows a backend 400 in the app and goes back to the details step", async () => {
    mockBackend({ status: 400, detail: "This does not look like a WhatsApp export." });
    const user = await analyse();
    expect(await screen.findByRole("alert")).toHaveTextContent("This does not look like a WhatsApp export.");
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("heading", { name: "Check details" })).toBeInTheDocument();
  });

  it("shows a connection problem and can try again", async () => {
    const fetchMock = mockBackend("network");
    const user = await analyse();
    expect(await screen.findByRole("alert")).toHaveTextContent("We could not reach the checker");
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    const analyseCalls = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/analyze"));
    expect(analyseCalls).toHaveLength(2);
  });
});
