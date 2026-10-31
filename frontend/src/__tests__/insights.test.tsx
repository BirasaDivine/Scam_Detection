import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { AnalyzeResult, Stats } from "../api";
import { InsightsPage } from "../InsightsPage";
import { RESULT } from "../test-utils";

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function backend(result: AnalyzeResult, originStatus = 204) {
  const fetchMock = vi.fn(async (url: string, _init?: RequestInit) => {
    if (url.endsWith("/health")) return json({ status: "ok", model_version: "mock-0", mock: false });
    if (url.endsWith("/origin")) return new Response(null, { status: originStatus });
    return json(result);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function analyse() {
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("tab", { name: /paste text/i }));
  await user.type(screen.getByLabelText("Chat text"), "Pay the fee");
  await user.click(screen.getByRole("button", { name: /next step/i }));
  await user.click(screen.getByRole("button", { name: "Analyse" }));
  return user;
}

describe("Scam source question", () => {
  it("is optional and sends only the chosen source", async () => {
    const fetchMock = backend({ ...RESULT, record_id: "abc" });
    const user = await analyse();
    const group = await screen.findByRole("group", { name: "Where did you get this message? (optional)" });
    expect(screen.getByRole("button", { name: "Save source" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Check another chat" })).toBeEnabled();

    await user.click(screen.getByRole("radio", { name: "Telegram" }));
    await user.click(screen.getByRole("button", { name: "Save source" }));
    expect(await screen.findByText("Thanks. This helps show where scams come from.")).toBeInTheDocument();
    expect(group).not.toBeInTheDocument();

    const [url, init] = fetchMock.mock.calls.find(([u]) => String(u).endsWith("/origin"))!;
    expect(url).toMatch(/\/checks\/abc\/origin$/);
    expect(JSON.parse(String(init?.body))).toEqual({ origin: "telegram" });
  });

  it("offers every source", async () => {
    backend({ ...RESULT, record_id: "abc" });
    await analyse();
    await screen.findByRole("group", { name: /where did you get this message/i });
    const names = screen.getAllByRole("radio").map((r) => r.closest("span")!.textContent);
    expect(names).toEqual(["WhatsApp", "SMS", "Telegram", "Facebook", "Instagram", "Email", "Phone call", "Other"]);
  });

  it("says so when saving fails", async () => {
    backend({ ...RESULT, record_id: "abc" }, 500);
    const user = await analyse();
    await user.click(await screen.findByRole("radio", { name: "WhatsApp" }));
    await user.click(screen.getByRole("button", { name: "Save source" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("We could not save the source.");
  });

  it("is not asked for a not scam verdict", async () => {
    backend({ ...RESULT, verdict: "not_scam", band: "low", record_id: "abc" });
    await analyse();
    await screen.findByRole("heading", { name: "This does not look like a scam" });
    expect(screen.queryByText(/where did you get this message/i)).not.toBeInTheDocument();
  });

  it("is not asked when the check was not counted", async () => {
    backend({ ...RESULT, record_id: null });
    await analyse();
    await screen.findByRole("heading", { name: "This looks like a scam" });
    expect(screen.queryByText(/where did you get this message/i)).not.toBeInTheDocument();
  });
});

const STATS: Stats = {
  total: 10,
  scam: 6,
  not_scam: 4,
  by_input_format: {
    whatsapp: { scam: 3, not_scam: 1 },
    plain: { scam: 1, not_scam: 2 },
    sms: { scam: 2, not_scam: 1 },
  },
  scam_origins: { whatsapp: 4, sms: 1, telegram: 0, facebook: 0, instagram: 0, email: 0, phone_call: 0, other: 0 },
  scam_origin_unreported: 1,
  recommendations: ["60% of checks were scams (6 of 10).", "Most reported scams came from WhatsApp (80%)."],
};

describe("Insights page", () => {
  it("asks for the token, then shows counts and recommendations", async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      const auth = new Headers(init?.headers).get("Authorization");
      return auth === "Bearer secret" ? json(STATS) : json({ detail: "Not allowed." }, 401);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<InsightsPage />);

    await user.type(screen.getByLabelText("Admin token"), "wrong");
    await user.click(screen.getByRole("button", { name: "Show insights" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("That token is not right.");

    await user.clear(screen.getByLabelText("Admin token"));
    await user.type(screen.getByLabelText("Admin token"), "secret");
    await user.click(screen.getByRole("button", { name: "Show insights" }));

    expect(await screen.findByText("Most reported scams came from WhatsApp (80%).")).toBeInTheDocument();
    expect(screen.getByText("All checks", { selector: "dt" }).nextElementSibling).toHaveTextContent("10");
    expect(screen.getByText("Scams", { selector: "dt" }).nextElementSibling).toHaveTextContent("6");
    expect(screen.getByText("Not scams", { selector: "dt" }).nextElementSibling).toHaveTextContent("4");
    expect(screen.getByText("1 scam check without a reported source.")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: "WhatsApp export 3 1" })).toBeInTheDocument();
    expect(sessionStorage.getItem("scamguard-admin-token")).toBe("secret");

    await user.click(screen.getByRole("button", { name: "Sign out" }));
    expect(screen.getByLabelText("Admin token")).toBeInTheDocument();
    expect(sessionStorage.getItem("scamguard-admin-token")).toBeNull();
  });

  it("explains when insights are off on the server", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => json({ detail: "Not allowed." }, 404)));
    const user = userEvent.setup();
    render(<InsightsPage />);
    await user.type(screen.getByLabelText("Admin token"), "x");
    await user.click(screen.getByRole("button", { name: "Show insights" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Insights are turned off on the server.");
  });
});
