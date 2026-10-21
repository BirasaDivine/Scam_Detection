import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { RESULT, WHATSAPP, chatFile, mockBackend } from "../test-utils";

afterEach(() => vi.unstubAllGlobals());

const fileInput = () => document.querySelector<HTMLInputElement>('input[type="file"]')!;

describe("Step 1: Add chat", () => {
  it("shows the empty upload state", () => {
    mockBackend();
    render(<App />);
    expect(screen.getByRole("tab", { name: /upload chat/i })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/attach a chat/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /next step/i })).not.toBeInTheDocument();
    expect(screen.getByText("Image upload: planned for a later version.")).toBeInTheDocument();
    expect(screen.getByText("ScamGuard, capstone research demonstration. English only.")).toBeInTheDocument();
  });

  it("shows a file row with name, message count and size, and removes it", async () => {
    mockBackend();
    const user = userEvent.setup();
    render(<App />);
    await user.upload(fileInput(), chatFile(WHATSAPP, "family.txt"));

    expect(await screen.findByText("family.txt")).toBeInTheDocument();
    expect(screen.getByText("2 messages")).toBeInTheDocument();
    expect(screen.getByText("2 messages").parentElement).toHaveTextContent(`2 messages · ${WHATSAPP.length} B`);
    expect(screen.getByRole("button", { name: /next step/i })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: "Remove family.txt" }));
    expect(screen.getByText(/attach a chat/i)).toBeInTheDocument();
  });

  it("refuses a file that is not .txt", async () => {
    mockBackend();
    const user = userEvent.setup({ applyAccept: false });
    render(<App />);
    await user.upload(fileInput(), chatFile("%PDF", "chat.pdf", "application/pdf"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Only .txt files are supported.");
  });

  it("refuses a file over 1 MB", async () => {
    mockBackend();
    const user = userEvent.setup();
    render(<App />);
    await user.upload(fileInput(), chatFile("a".repeat(1024 * 1024 + 1)));
    expect(await screen.findByRole("alert")).toHaveTextContent("larger than 1 MB");
  });

  it("has a labelled textarea with a character counter on the paste tab", async () => {
    mockBackend();
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("tab", { name: /paste text/i }));
    const box = screen.getByLabelText("Chat text");
    await user.type(box, "Hello");
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(box).toHaveAccessibleDescription(/one message per line.*5 characters/i);
    expect(screen.getByRole("button", { name: /next step/i })).toBeEnabled();
  });
});

describe("Step 2: Check details", () => {
  it("offers the three chat sources, preselects a guess and shows the privacy note", async () => {
    mockBackend();
    const user = userEvent.setup();
    render(<App />);
    await user.upload(fileInput(), chatFile(WHATSAPP));
    await user.click(await screen.findByRole("button", { name: /next step/i }));

    expect(screen.getByRole("heading", { name: "Check details" })).toHaveFocus();
    const group = screen.getByRole("group", { name: "Chat source" });
    expect(within(group).getAllByRole("radio")).toHaveLength(3);
    expect(within(group).getByRole("radio", { name: /whatsapp export/i })).toBeChecked();
    expect(screen.getByText("Your chat is analysed in memory and is not stored.")).toBeInTheDocument();
  });

  it("goes back to step 1 and keeps the chat", async () => {
    mockBackend();
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("tab", { name: /paste text/i }));
    await user.type(screen.getByLabelText("Chat text"), "Send the fee now");
    await user.click(screen.getByRole("button", { name: /next step/i }));
    expect(screen.getByRole("radio", { name: /single sms/i })).toBeChecked();

    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByLabelText("Chat text")).toHaveValue("Send the fee now");
  });
});

describe("Step 3: Result", () => {
  async function analyseText(text: string) {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("tab", { name: /paste text/i }));
    await user.type(screen.getByLabelText("Chat text"), text);
    await user.click(screen.getByRole("button", { name: /next step/i }));
    await user.click(screen.getByRole("button", { name: "Analyse" }));
    return user;
  }

  it("shows the verdict, band, pieces, model version and disclaimer in a live region", async () => {
    const fetchMock = mockBackend();
    const user = await analyseText("Pay the fee");

    const heading = await screen.findByRole("heading", { name: "This looks like a scam" });
    expect(heading.closest("[aria-live]")).toHaveAttribute("aria-live", "polite");
    expect(screen.getByText("Confidence band:")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByText("Pieces scored").nextElementSibling).toHaveTextContent(/^3$/);
    expect(screen.getByText("Model").nextElementSibling).toHaveTextContent(/^mock-0$/);
    expect(screen.getByText(RESULT.disclaimer)).toBeInTheDocument();

    const [, init] = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/analyze"))!;
    expect(JSON.parse(String(init?.body))).toEqual({ text: "Pay the fee", source: "sms" });

    await user.click(screen.getByRole("button", { name: "Check another chat" }));
    expect(screen.getByText(/attach a chat/i)).toBeInTheDocument();
  });

  it.each([
    ["medium", "This looks like a scam", "Medium"],
    ["borderline", "This does not look like a scam", "Borderline"],
    ["low", "This does not look like a scam", "Low"],
  ] as const)("shows the %s band", async (band, title, label) => {
    mockBackend({ ...RESULT, band, verdict: band === "medium" ? "scam" : "not_scam" });
    await analyseText("hello");
    expect(await screen.findByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("shows a loading state while waiting", async () => {
    let release!: (r: Response) => void;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        url.endsWith("/health")
          ? Promise.reject(new TypeError("offline"))
          : new Promise<Response>((resolve) => (release = resolve)),
      ),
    );
    await analyseText("hello");
    expect(screen.getByRole("heading", { name: "Checking the chat" })).toBeInTheDocument();
    expect(screen.getByText("This can take a few seconds.")).toBeInTheDocument();
    release(new Response(JSON.stringify(RESULT), { status: 200 }));
    expect(await screen.findByRole("heading", { name: "This looks like a scam" })).toBeInTheDocument();
  });

  it("uploads the file itself when the upload tab is used", async () => {
    const fetchMock = mockBackend();
    const user = userEvent.setup();
    render(<App />);
    await user.upload(fileInput(), chatFile(WHATSAPP));
    await user.click(await screen.findByRole("button", { name: /next step/i }));
    await user.click(screen.getByRole("button", { name: "Analyse" }));
    await screen.findByRole("heading", { name: "This looks like a scam" });

    const [, init] = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/analyze"))!;
    const form = init?.body as FormData;
    expect((form.get("file") as File).name).toBe("chat.txt");
    expect(form.get("source")).toBe("whatsapp");
  });
});

describe("Mock mode", () => {
  it("shows the MOCK MODEL banner when the backend runs the mock scorer", async () => {
    mockBackend(RESULT, true);
    render(<App />);
    expect(await screen.findByText("MOCK MODEL.")).toBeInTheDocument();
  });

  it("hides the banner for a real model", async () => {
    const fetchMock = mockBackend(RESULT, false);
    render(<App />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(screen.queryByText("MOCK MODEL.")).not.toBeInTheDocument();
  });
});
