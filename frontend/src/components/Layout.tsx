import { Equals, FolderOpen, Info, ListChecks, ShieldCheck, X } from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState } from "react";
import styles from "./Layout.module.css";

export function MockBanner() {
  return (
    <div className={styles.mockBanner} role="note">
      <Info size={18} aria-hidden="true" />
      <p>
        <strong>MOCK MODEL.</strong> Results are fake and only show how the app works.
      </p>
    </div>
  );
}

/** Chip on the left, menu on the right. The menu opens a short About panel. */
export function TopBar() {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const button = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className={styles.topBarWrap}>
      <div className={styles.topBar}>
        <span className={styles.chip}>
          <ShieldCheck size={16} aria-hidden="true" />
          Research demo
        </span>
        <button
          ref={button}
          type="button"
          className={styles.menuButton}
          aria-expanded={open}
          aria-controls={panelId}
          aria-label={open ? "Close about" : "About ScamGuard"}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? <X size={22} aria-hidden="true" /> : <Equals size={22} aria-hidden="true" />}
        </button>
      </div>
      <div id={panelId} className={styles.about} hidden={!open}>
        <h2 className={styles.aboutTitle}>About ScamGuard</h2>
        <p>
          ScamGuard is a capstone research demonstration. It reads an English chat and gives one verdict, scam or not
          scam, with a confidence band.
        </p>
        <p>It is not a proven detector and it can be wrong. Your chat is analysed in memory and is not stored.</p>
      </div>
    </div>
  );
}

// Flat field of 0s and 1s behind the hero icon. It thins out towards the edges
// by leaving characters out, not by fading, so there is no gradient.
const PATTERN = (() => {
  const cols = 27;
  const rows = 11;
  const lines: string[] = [];
  for (let r = 0; r < rows; r++) {
    const cells: string[] = [];
    for (let c = 0; c < cols; c++) {
      // integer hash, so the field is stable between renders
      let h = Math.imul(r + 1, 374761393) + Math.imul(c + 1, 668265263);
      h = Math.imul(h ^ (h >>> 13), 1274126177);
      h ^= h >>> 16;
      const noise = (h & 0xffff) / 0x10000;
      const dx = (c - (cols - 1) / 2) / (cols / 2);
      const dy = (r - (rows - 1) / 2) / (rows / 2);
      const keep = 1 - Math.sqrt(dx * dx + dy * dy);
      cells.push(noise < keep * 2.4 + 0.12 ? String((h >>> 17) & 1) : " ");
    }
    lines.push(cells.join(" "));
  }
  return lines.join("\n");
})();

export function Hero({ illustrated }: { illustrated: boolean }) {
  return (
    <header className={styles.hero} data-illustrated={illustrated || undefined}>
      <div className={styles.art} aria-hidden="true">
        <pre className={styles.pattern}>{PATTERN}</pre>
        <span className={styles.artIcon}>
          <ShieldCheck size={96} />
        </span>
      </div>
      <h1 className={styles.title}>ScamGuard</h1>
      <p className={styles.tagline}>Check a chat for signs of a scam.</p>
    </header>
  );
}

export type Step = 1 | 2 | 3;

const STEPS = [
  { n: 1, label: "Add chat", icon: FolderOpen },
  { n: 2, label: "Check details", icon: ListChecks },
  { n: 3, label: "Result", icon: ShieldCheck },
] as const;

interface StepBarProps {
  current: Step;
  onGo: (step: Step) => void;
  locked: boolean;
}

/** Floating bar showing the three steps. Earlier steps can be revisited. */
export function StepBar({ current, onGo, locked }: StepBarProps) {
  return (
    <nav className={styles.stepBar} aria-label="Progress">
      <ol>
        {STEPS.map(({ n, label, icon: StepIcon }) => {
          const isCurrent = n === current;
          const reachable = n < current && !locked;
          return (
            <li key={n}>
              <button
                type="button"
                className={styles.stepButton}
                aria-current={isCurrent ? "step" : undefined}
                aria-disabled={!reachable || undefined}
                title={label}
                onClick={() => reachable && onGo(n)}
              >
                <StepIcon size={22} weight={isCurrent ? "bold" : "regular"} aria-hidden="true" />
                <span className="visually-hidden">
                  Step {n}: {label}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export function Footer() {
  return (
    <footer className={styles.footer}>
      <p>ScamGuard, capstone research demonstration. English only.</p>
    </footer>
  );
}
