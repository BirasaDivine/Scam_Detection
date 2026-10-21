import type { Source } from "./api";

export const MAX_BYTES = 1024 * 1024;

// Light check only. The backend does the real parsing.
const WHATSAPP_HEADER = /^[\u200e\u200f]?\[?\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4},?\s+\d{1,2}[:.]\d{2}/;

function lines(text: string): string[] {
  return text
    .split(/\r\n|\r|\n/)
    .map((l) => l.trim())
    .filter(Boolean);
}

export function guessSource(text: string): Source {
  const all = lines(text);
  if (all.some((l) => WHATSAPP_HEADER.test(l))) return "whatsapp";
  return all.length <= 1 ? "sms" : "plain";
}

export function countMessages(text: string, source: Source = guessSource(text)): number {
  const all = lines(text);
  if (source === "sms") return all.length ? 1 : 0;
  if (source === "whatsapp") return all.filter((l) => WHATSAPP_HEADER.test(l)).length;
  return all.length;
}

export function byteLength(text: string): number {
  return new TextEncoder().encode(text).length;
}

export function formatSize(bytes: number): [value: string, unit: string] {
  if (bytes < 1024) return [String(bytes), "B"];
  if (bytes < 1024 * 1024) return [(bytes / 1024).toFixed(1), "KB"];
  return [(bytes / (1024 * 1024)).toFixed(2), "MB"];
}

export function formatCount(n: number): string {
  return n.toLocaleString("en-US");
}

export function plural(n: number, one: string, many: string): string {
  return `${formatCount(n)} ${n === 1 ? one : many}`;
}

export function readFileText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}
