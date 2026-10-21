import type { Band, Source, Verdict } from "./api";

// UI copy: short, plain sentences. No exclamation marks, no em dashes.

export const SOURCES: { id: Source; label: string; hint: string }[] = [
  { id: "whatsapp", label: "WhatsApp export", hint: "A .txt file exported from a WhatsApp chat." },
  { id: "plain", label: "Plain text", hint: "Each line is read as one message." },
  { id: "sms", label: "Single SMS", hint: "The whole text is read as one message." },
];

export const VERDICT_TITLE: Record<Verdict, string> = {
  scam: "This looks like a scam",
  not_scam: "This does not look like a scam",
};

export const BAND_LABEL: Record<Band, string> = {
  high: "High",
  medium: "Medium",
  borderline: "Borderline",
  low: "Low",
};

export const BAND_SEGMENTS: Record<Band, number> = { high: 4, medium: 3, borderline: 2, low: 1 };

interface ErrorCopy {
  title: string;
  fallback: string;
  retry: boolean;
}

const ERRORS: Record<number, ErrorCopy> = {
  0: {
    title: "We could not reach the checker",
    fallback: "Check your connection and try again.",
    retry: true,
  },
  400: {
    title: "We could not read this chat",
    fallback: "Check the chat and the chat source, then try again.",
    retry: false,
  },
  413: {
    title: "This chat is too large",
    fallback: "Try a shorter chat. The limit is 1 MB or 2,000 messages.",
    retry: false,
  },
  415: {
    title: "This file type is not supported",
    fallback: "Only .txt files are supported.",
    retry: false,
  },
  422: {
    title: "Some details are missing",
    fallback: "Go back and check the chat source.",
    retry: false,
  },
  500: {
    title: "Something went wrong",
    fallback: "Please try again in a moment.",
    retry: true,
  },
  504: {
    title: "The check took too long",
    fallback: "Try a shorter chat.",
    retry: true,
  },
};

export function errorCopy(status: number): ErrorCopy {
  return ERRORS[status] ?? ERRORS[500];
}
