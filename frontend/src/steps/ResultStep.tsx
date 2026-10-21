import {
  ArrowCounterClockwise,
  ArrowLeft,
  ArrowsClockwise,
  CheckCircle,
  Info,
  Question,
  WarningCircle,
  WarningOctagon,
} from "@phosphor-icons/react";
import type { AnalyzeResult, Band } from "../api";
import { formatCount } from "../chat";
import { ConfidenceBar } from "../components/ConfidenceBar";
import ui from "../components/ui.module.css";
import { VERDICT_TITLE, errorCopy } from "../copy";
import styles from "./ResultStep.module.css";

export type Outcome =
  | { state: "loading" }
  | { state: "done"; result: AnalyzeResult }
  | { state: "error"; status: number; detail: string };

interface Props {
  outcome: Outcome;
  onCancel: () => void;
  onBack: () => void;
  onRetry: () => void;
  onRestart: () => void;
}

/** Lets a long model name wrap after an underscore instead of in the middle of a word. */
function breakable(text: string) {
  return text.split("_").flatMap((part, i) => (i === 0 ? [part] : ["_", <wbr key={i} />, part]));
}

/** The live region stays mounted from loading to result, so the change is announced. */
export function ResultStep(props: Props) {
  return (
    <section aria-labelledby="step-heading" className={ui.card}>
      <div aria-live="polite" aria-atomic="true">
        <StepBody {...props} />
      </div>
    </section>
  );
}

function StepBody({ outcome, onCancel, onBack, onRetry, onRestart }: Props) {
  if (outcome.state === "loading") return <Loading onCancel={onCancel} />;
  if (outcome.state === "error") {
    return <ErrorState status={outcome.status} detail={outcome.detail} onBack={onBack} onRetry={onRetry} />;
  }
  return <Result result={outcome.result} onRestart={onRestart} />;
}

function Loading({ onCancel }: { onCancel: () => void }) {
  return (
    <div className={styles.loading}>
      <h2 id="step-heading" className={ui.cardTitle} tabIndex={-1} data-step-heading>
        Checking the chat
      </h2>
      <p className={ui.hint}>This can take a few seconds.</p>
      <div className={styles.skeleton} aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className={ui.actions}>
        <button type="button" className={ui.textButton} onClick={onCancel}>
          <ArrowLeft size={18} aria-hidden="true" />
          Cancel
        </button>
      </div>
    </div>
  );
}

const BAND_ICON: Record<Band, typeof CheckCircle> = {
  high: WarningOctagon,
  medium: WarningOctagon,
  borderline: Question,
  low: CheckCircle,
};

function Result({ result, onRestart }: { result: AnalyzeResult; onRestart: () => void }) {
  const VerdictIcon = BAND_ICON[result.band];
  return (
    <div className={styles.result}>
      <h2 id="step-heading" className={styles.verdict} data-band={result.band} tabIndex={-1} data-step-heading>
        <VerdictIcon size={32} aria-hidden="true" />
        {VERDICT_TITLE[result.verdict]}
      </h2>

      <ConfidenceBar band={result.band} />

      <dl className={styles.facts}>
        <div>
          <dt>Pieces scored</dt>
          <dd className={ui.mono}>{formatCount(result.pieces_scored)}</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd className={`${ui.mono} ${styles.small}`}>{breakable(result.model_version)}</dd>
        </div>
      </dl>

      <p className={ui.note}>
        <Info size={18} aria-hidden="true" />
        {result.disclaimer}
      </p>

      <div className={ui.actions}>
        <button type="button" className={`${ui.textButton} ${ui.actionsEnd}`} onClick={onRestart}>
          <ArrowCounterClockwise size={18} aria-hidden="true" />
          Check another chat
        </button>
      </div>
    </div>
  );
}

interface ErrorProps {
  status: number;
  detail: string;
  onBack: () => void;
  onRetry: () => void;
}

function ErrorState({ status, detail, onBack, onRetry }: ErrorProps) {
  const copy = errorCopy(status);
  return (
    <div role="alert" className={styles.error}>
      <h2 id="step-heading" className={styles.errorTitle} tabIndex={-1} data-step-heading>
        <WarningCircle size={28} aria-hidden="true" />
        {copy.title}
      </h2>
      <p>{detail || copy.fallback}</p>
      <div className={ui.actions}>
        <button type="button" className={ui.textButton} onClick={onBack}>
          <ArrowLeft size={18} aria-hidden="true" />
          Back
        </button>
        {copy.retry && (
          <button type="button" className={ui.textButton} onClick={onRetry}>
            <ArrowsClockwise size={18} aria-hidden="true" />
            Try again
          </button>
        )}
      </div>
    </div>
  );
}
