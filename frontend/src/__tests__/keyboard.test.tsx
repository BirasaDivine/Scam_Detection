import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { mockBackend } from "../test-utils";

afterEach(() => vi.unstubAllGlobals());

describe("keyboard", () => {
  it("moves between tabs with arrow keys, Home and End", async () => {
    mockBackend();
    const user = userEvent.setup();
    render(<App />);
    const upload = screen.getByRole("tab", { name: /upload chat/i });
    const paste = screen.getByRole("tab", { name: /paste text/i });

    await user.tab(); // About menu
    await user.tab();
    expect(upload).toHaveFocus();
    expect(paste).toHaveAttribute("tabindex", "-1"); // one tab stop for the whole list

    await user.keyboard("{ArrowRight}");
    expect(paste).toHaveFocus();
    expect(paste).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveAttribute("aria-labelledby", paste.id);

    await user.keyboard("{ArrowRight}"); // wraps around
    expect(upload).toHaveFocus();
    await user.keyboard("{End}");
    expect(paste).toHaveFocus();
    await user.keyboard("{Home}");
    expect(upload).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{ArrowLeft}");
    expect(paste).toHaveAttribute("aria-selected", "true");
  });

  it("changes the chat source with arrow keys", async () => {
    mockBackend();
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("tab", { name: /paste text/i }));
    await user.type(screen.getByLabelText("Chat text"), "one{Enter}two");
    await user.click(screen.getByRole("button", { name: /next step/i }));

    const plain = screen.getByRole("radio", { name: /plain text/i });
    expect(plain).toBeChecked();
    plain.focus();
    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("radio", { name: /single sms/i })).toBeChecked();
    await user.keyboard("{ArrowUp}{ArrowUp}");
    expect(screen.getByRole("radio", { name: /whatsapp export/i })).toBeChecked();
  });

  it("completes the whole flow with the keyboard only", async () => {
    mockBackend();
    const user = userEvent.setup();
    render(<App />);

    await user.tab(); // About menu
    await user.tab(); // Upload chat tab
    await user.keyboard("{ArrowRight}"); // Paste text tab
    await user.tab(); // textarea
    await user.keyboard("Your account is blocked, pay the fee");
    await user.tab(); // Next step
    expect(screen.getByRole("button", { name: /next step/i })).toHaveFocus();
    await user.keyboard("{Enter}");

    expect(screen.getByRole("heading", { name: "Check details" })).toHaveFocus();
    await user.tab(); // checked radio
    expect(screen.getByRole("radio", { name: /single sms/i })).toHaveFocus();
    await user.tab(); // Change the chat
    await user.tab(); // Back
    await user.tab(); // Analyse
    expect(screen.getByRole("button", { name: "Analyse" })).toHaveFocus();
    await user.keyboard("{Enter}");

    const verdict = await screen.findByRole("heading", { name: "This looks like a scam" });
    expect(verdict).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Check another chat" })).toHaveFocus();
  });

  it("opens and closes the About panel, and Escape returns focus to the menu", async () => {
    mockBackend();
    const user = userEvent.setup();
    render(<App />);
    const menu = screen.getByRole("button", { name: "About ScamGuard" });
    await user.click(menu);
    expect(menu).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("heading", { name: "About ScamGuard" })).toBeVisible();
    await user.keyboard("{Escape}");
    expect(menu).toHaveAttribute("aria-expanded", "false");
    expect(menu).toHaveFocus();
  });

  it("shows progress in the step bar and only allows going back", async () => {
    mockBackend();
    const user = userEvent.setup();
    render(<App />);
    const bar = screen.getByRole("navigation", { name: "Progress" });
    const step = (n: number) => within(bar).getByRole("button", { name: new RegExp(`^Step ${n}`) });
    expect(step(1)).toHaveAttribute("aria-current", "step");
    expect(step(2)).toHaveAttribute("aria-disabled", "true");

    await user.click(step(2)); // future steps do nothing
    expect(step(1)).toHaveAttribute("aria-current", "step");

    await user.click(screen.getByRole("tab", { name: /paste text/i }));
    await user.type(screen.getByLabelText("Chat text"), "hello");
    await user.click(screen.getByRole("button", { name: /next step/i }));
    expect(step(2)).toHaveAttribute("aria-current", "step");

    await user.click(step(1));
    expect(screen.getByLabelText("Chat text")).toHaveValue("hello");
  });
});
