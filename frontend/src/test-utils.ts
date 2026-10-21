import { vi } from "vitest";
import type { AnalyzeResult } from "./api";

export const RESULT: AnalyzeResult = {
  verdict: "scam",
  band: "high",
  pieces_scored: 3,
  source_rule: "dialogue",
  model_version: "mock-0",
  disclaimer:
    "This is a research demonstration. It has not been validated for use in Africa, and it can be wrong.",
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

type AnalyzeReply = AnalyzeResult | { status: number; detail?: string } | "network";

/** Stubs fetch: /health answers with `mock`, /analyze with `reply`. Returns the mock for inspection. */
export function mockBackend(reply: AnalyzeReply = RESULT, mock = false) {
  const fetchMock = vi.fn(async (url: string, _init?: RequestInit) => {
    if (url.endsWith("/health")) return json({ status: "ok", model_version: "mock-0", mock });
    if (reply === "network") throw new TypeError("Failed to fetch");
    if ("status" in reply) return json(reply.detail ? { detail: reply.detail } : {}, reply.status);
    return json(reply);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export const chatFile = (content: string, name = "chat.txt", type = "text/plain") =>
  new File([content], name, { type });

export const WHATSAPP = "12/03/2024, 14:05 - Ann: Your account is blocked\n12/03/2024, 14:06 - Bo: ok\n";
