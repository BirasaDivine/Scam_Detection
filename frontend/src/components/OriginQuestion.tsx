import { CheckCircle, WarningCircle } from "@phosphor-icons/react";
import { useId, useState } from "react";
import { setOrigin, type Origin } from "../api";
import { ORIGINS } from "../copy";
import radio from "./SourceRadio.module.css";
import ui from "./ui.module.css";
import styles from "./OriginQuestion.module.css";

type State = "idle" | "saving" | "saved" | "error";

/** Optional. Only the chosen source is sent, never the chat. */
export function OriginQuestion({ recordId }: { recordId: string }) {
  const [choice, setChoice] = useState<Origin | null>(null);
  const [state, setState] = useState<State>("idle");
  const name = useId();
  const hintId = useId();

  if (state === "saved") {
    return (
      <p className={`${ui.note} ${styles.saved}`} role="status">
        <CheckCircle size={18} aria-hidden="true" />
        Thanks. This helps show where scams come from.
      </p>
    );
  }

  async function save() {
    if (!choice) return;
    setState("saving");
    try {
      await setOrigin(recordId, choice);
      setState("saved");
    } catch {
      setState("error");
    }
  }

  return (
    <fieldset className={`${radio.fieldset} ${styles.box}`} aria-describedby={hintId}>
      <legend className={styles.legend}>Where did you get this message? (optional)</legend>
      <p id={hintId} className={styles.hint}>
        Only the source is saved, never the message.
      </p>
      <div className={radio.options}>
        {ORIGINS.map((o) => {
          const id = `${name}-${o.id}`;
          return (
            <span key={o.id} className={radio.option}>
              <input
                id={id}
                type="radio"
                name={name}
                value={o.id}
                checked={choice === o.id}
                onChange={() => setChoice(o.id)}
                className={radio.radio}
              />
              <label htmlFor={id}>{o.label}</label>
            </span>
          );
        })}
      </div>
      {state === "error" && (
        <p className={ui.fieldError} role="alert">
          <WarningCircle size={18} aria-hidden="true" />
          We could not save the source. You can try again.
        </p>
      )}
      <button
        type="button"
        className={`${ui.secondaryButton} ${styles.save}`}
        onClick={save}
        disabled={!choice || state === "saving"}
      >
        {state === "saving" ? "Saving" : "Save source"}
      </button>
    </fieldset>
  );
}
