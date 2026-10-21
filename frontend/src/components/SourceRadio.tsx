import { useId } from "react";
import type { Source } from "../api";
import { SOURCES } from "../copy";
import styles from "./SourceRadio.module.css";

/** Inline radios, as in the reference's "Security Type" card. The chosen option's hint shows below. */
export function SourceRadio({ value, onChange }: { value: Source; onChange: (s: Source) => void }) {
  const name = useId();
  const hintId = useId();
  const selected = SOURCES.find((s) => s.id === value);
  return (
    <fieldset className={styles.fieldset} aria-describedby={hintId}>
      <legend className={styles.legend}>Chat source</legend>
      <div className={styles.options}>
        {SOURCES.map((s) => {
          const id = `${name}-${s.id}`;
          return (
            <span key={s.id} className={styles.option}>
              <input
                id={id}
                type="radio"
                name={name}
                value={s.id}
                checked={value === s.id}
                onChange={() => onChange(s.id)}
                className={styles.radio}
              />
              <label htmlFor={id}>{s.label}</label>
            </span>
          );
        })}
      </div>
      <p id={hintId} className={styles.hint}>
        {selected?.hint}
      </p>
    </fieldset>
  );
}
