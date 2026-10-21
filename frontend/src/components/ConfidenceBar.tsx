import type { Band } from "../api";
import { BAND_LABEL, BAND_SEGMENTS } from "../copy";
import styles from "./ConfidenceBar.module.css";

/** Takes the place of the reference's "Strength" line. The text label carries the meaning; colour repeats it. */
export function ConfidenceBar({ band }: { band: Band }) {
  const filled = BAND_SEGMENTS[band];
  return (
    <div className={styles.wrap}>
      <div className={styles.bar} data-band={band} aria-hidden="true">
        {[1, 2, 3, 4].map((n) => (
          <span key={n} className={styles.segment} data-filled={n <= filled || undefined} />
        ))}
      </div>
      <p className={styles.text}>
        <span className={styles.caption}>Confidence band:</span>{" "}
        <span className={styles.label} data-band={band}>
          {BAND_LABEL[band]}
        </span>
        <span className="visually-hidden"> ({filled} of 4)</span>
      </p>
    </div>
  );
}
