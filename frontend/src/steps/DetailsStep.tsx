import { ArrowLeft, ArrowRight, ClipboardText, FileText, Info, PencilSimple } from "@phosphor-icons/react";
import type { Source } from "../api";
import { SourceRadio } from "../components/SourceRadio";
import ui from "../components/ui.module.css";
import styles from "./DetailsStep.module.css";

export interface ChatSummary {
  kind: "file" | "text";
  label: string;
}

interface Props {
  source: Source;
  onSource: (s: Source) => void;
  summary: ChatSummary;
  onBack: () => void;
  onAnalyse: () => void;
}

/** Laid out like the reference's "Security Type" card. */
export function DetailsStep({ source, onSource, summary, onBack, onAnalyse }: Props) {
  const SummaryIcon = summary.kind === "file" ? FileText : ClipboardText;
  return (
    <section aria-labelledby="step-heading" className={ui.card}>
      <h2 id="step-heading" className="visually-hidden" tabIndex={-1} data-step-heading>
        Check details
      </h2>
      <SourceRadio value={source} onChange={onSource} />

      <div className={styles.summaryRow}>
        <p className={styles.summary}>
          <SummaryIcon size={20} aria-hidden="true" />
          <span className="visually-hidden">Chat: </span>
          <span className={styles.summaryText}>{summary.label}</span>
        </p>
        <button type="button" className={styles.editButton} onClick={onBack} aria-label="Change the chat">
          <PencilSimple size={20} aria-hidden="true" />
        </button>
      </div>

      <p className={styles.privacy}>
        <Info size={18} aria-hidden="true" />
        Your chat is analysed in memory and is not stored.
      </p>

      <div className={ui.actions}>
        <button type="button" className={ui.textButton} onClick={onBack}>
          <ArrowLeft size={18} aria-hidden="true" />
          Back
        </button>
        <button type="button" className={ui.textButton} onClick={onAnalyse}>
          Analyse
          <ArrowRight size={18} weight="bold" aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}
