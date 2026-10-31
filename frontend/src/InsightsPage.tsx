import { ArrowsClockwise, Lightbulb, LockSimple, SignOut, WarningCircle } from "@phosphor-icons/react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ApiError, getStats, type Stats } from "./api";
import { formatCount } from "./chat";
import ui from "./components/ui.module.css";
import { ORIGINS, SOURCES } from "./copy";
import app from "./App.module.css";
import styles from "./InsightsPage.module.css";

const TOKEN_KEY = "scamguard-admin-token";

function readToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

function writeToken(token: string) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // private mode: the token lasts until the page is closed
  }
}

function failure(err: unknown) {
  const status = err instanceof ApiError ? err.status : 0;
  if (status === 401) return "That token is not right.";
  if (status === 404) return "Insights are turned off on the server. Set SCAMGUARD_ADMIN_TOKEN to turn them on.";
  if (status === 0) return "We could not reach the checker. Check your connection and try again.";
  return "The counts could not be loaded. Please try again.";
}

const percent = (part: number, whole: number) => (whole ? Math.round((100 * part) / whole) : 0);

/** Hidden admin page, opened at #insights. Shows counts only, never chat text. */
export function InsightsPage() {
  const [token, setToken] = useState(readToken);
  const [draft, setDraft] = useState("");
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (value: string, signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const result = await getStats(value, signal);
      setStats(result);
      setToken(value);
      writeToken(value);
    } catch (err) {
      if (signal?.aborted) return;
      setStats(null);
      setError(failure(err));
      if (err instanceof ApiError && err.status === 401) {
        setToken("");
        writeToken("");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const saved = readToken();
    if (!saved) return;
    const controller = new AbortController();
    load(saved, controller.signal);
    return () => controller.abort();
  }, [load]);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (draft.trim()) load(draft.trim());
  }

  function signOut() {
    setToken("");
    setStats(null);
    setDraft("");
    writeToken("");
  }

  return (
    <div className={app.page}>
      <main className={`${app.main} ${styles.main}`}>
        <h1 className={styles.title}>Insights</h1>
        <p className={ui.hint}>Counts of checks and where reported scams came from. No chat text is stored.</p>

        {!stats && (
          <form className={`${ui.card} ${styles.form}`} onSubmit={submit}>
            <label htmlFor="admin-token" className={styles.label}>
              Admin token
            </label>
            <input
              id="admin-token"
              type="password"
              autoComplete="current-password"
              className={styles.input}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
            {error && (
              <p className={ui.fieldError} role="alert">
                <WarningCircle size={18} aria-hidden="true" />
                {error}
              </p>
            )}
            <button type="submit" className={`${ui.primaryButton} ${styles.submit}`} disabled={loading}>
              <LockSimple size={18} aria-hidden="true" />
              {loading ? "Loading" : "Show insights"}
            </button>
          </form>
        )}

        {stats && <StatsView stats={stats} />}

        {stats && (
          <div className={ui.actions}>
            <button type="button" className={ui.textButton} onClick={() => load(token)} disabled={loading}>
              <ArrowsClockwise size={18} aria-hidden="true" />
              Refresh
            </button>
            <button type="button" className={ui.textButton} onClick={signOut}>
              <SignOut size={18} aria-hidden="true" />
              Sign out
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

function StatsView({ stats }: { stats: Stats }) {
  const reported = ORIGINS.reduce((sum, o) => sum + stats.scam_origins[o.id], 0);
  const max = Math.max(1, ...ORIGINS.map((o) => stats.scam_origins[o.id]));
  const origins = [...ORIGINS].sort((a, b) => stats.scam_origins[b.id] - stats.scam_origins[a.id]);

  return (
    <>
      <section className={ui.card} aria-labelledby="totals">
        <h2 id="totals" className={ui.cardTitle}>
          Checks
        </h2>
        <dl className={styles.tiles}>
          <div>
            <dt>All checks</dt>
            <dd>{formatCount(stats.total)}</dd>
          </div>
          <div>
            <dt>Scams</dt>
            <dd>{formatCount(stats.scam)}</dd>
            <span className={styles.sub}>{percent(stats.scam, stats.total)}%</span>
          </div>
          <div>
            <dt>Not scams</dt>
            <dd>{formatCount(stats.not_scam)}</dd>
            <span className={styles.sub}>{percent(stats.not_scam, stats.total)}%</span>
          </div>
        </dl>
      </section>

      <section className={ui.card} aria-labelledby="advice">
        <h2 id="advice" className={ui.cardTitle}>
          Recommendations
        </h2>
        <ul className={styles.tips}>
          {stats.recommendations.map((tip) => (
            <li key={tip}>
              <Lightbulb size={18} aria-hidden="true" />
              {tip}
            </li>
          ))}
        </ul>
      </section>

      <section className={ui.card} aria-labelledby="origins">
        <h2 id="origins" className={ui.cardTitle}>
          Where reported scams came from
        </h2>
        <ul className={styles.bars}>
          {origins.map((o) => {
            const n = stats.scam_origins[o.id];
            return (
              <li key={o.id} title={`${o.label}: ${n} (${percent(n, reported)}% of reported scams)`}>
                <span className={styles.barLabel}>{o.label}</span>
                <span className={styles.track} aria-hidden="true">
                  {n > 0 && <span className={styles.bar} style={{ width: `${(100 * n) / max}%` }} />}
                </span>
                <span className={`${ui.mono} ${styles.barValue}`}>{formatCount(n)}</span>
              </li>
            );
          })}
        </ul>
        <p className={`${ui.hint} ${styles.footnote}`}>
          {formatCount(stats.scam_origin_unreported)} scam {stats.scam_origin_unreported === 1 ? "check" : "checks"}{" "}
          without a reported source.
        </p>
      </section>

      <section className={ui.card} aria-labelledby="formats">
        <h2 id="formats" className={ui.cardTitle}>
          By chat format
        </h2>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Format</th>
              <th scope="col">Scams</th>
              <th scope="col">Not scams</th>
            </tr>
          </thead>
          <tbody>
            {SOURCES.map((s) => (
              <tr key={s.id}>
                <th scope="row">{s.label}</th>
                <td className={ui.mono}>{formatCount(stats.by_input_format[s.id].scam)}</td>
                <td className={ui.mono}>{formatCount(stats.by_input_format[s.id].not_scam)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
