export type Source = "whatsapp" | "plain" | "sms";
export type Verdict = "scam" | "not_scam";
export type Band = "high" | "medium" | "borderline" | "low";

export interface AnalyzeResult {
  verdict: Verdict;
  band: Band;
  pieces_scored: number;
  source_rule: "sms" | "dialogue";
  model_version: string;
  disclaimer: string;
}

export interface Health {
  status: "ok";
  model_version: string;
  mock: boolean;
}

/** status 0 means the backend could not be reached. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(`API error ${status}`);
  }
}

const BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
// A little longer than the backend's own timeout, so its 504 normally arrives first.
const CLIENT_TIMEOUT_MS = 30_000;

export async function getHealth(signal?: AbortSignal): Promise<Health> {
  const res = await fetch(`${BASE}/health`, { signal });
  if (!res.ok) throw new ApiError(res.status, "");
  return res.json();
}

export type AnalyzeInput = { file: File; source: Source } | { text: string; source: Source };

export async function analyze(input: AnalyzeInput, signal: AbortSignal): Promise<AnalyzeResult> {
  let init: RequestInit;
  if ("file" in input) {
    const form = new FormData();
    form.append("file", input.file, input.file.name);
    form.append("source", input.source);
    init = { method: "POST", body: form };
  } else {
    init = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: input.text, source: input.source }),
    };
  }

  const inner = new AbortController();
  const timer = setTimeout(() => inner.abort(), CLIENT_TIMEOUT_MS);
  const forward = () => inner.abort();
  signal.addEventListener("abort", forward);

  let res: Response;
  try {
    res = await fetch(`${BASE}/analyze`, { ...init, signal: inner.signal });
  } catch {
    if (signal.aborted) throw new DOMException("Cancelled", "AbortError");
    throw new ApiError(inner.signal.aborted ? 504 : 0, "");
  } finally {
    clearTimeout(timer);
    signal.removeEventListener("abort", forward);
  }

  if (res.ok) return res.json();
  let detail = "";
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") detail = body.detail;
  } catch {
    // no JSON body, the fallback copy is used
  }
  throw new ApiError(res.status, detail);
}
