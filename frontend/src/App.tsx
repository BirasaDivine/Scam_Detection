import { useEffect, useRef, useState } from "react";
import { ApiError, analyze, getHealth, type Source } from "./api";
import { formatCount, guessSource, plural } from "./chat";
import { Footer, Hero, MockBanner, StepBar, TopBar, type Step } from "./components/Layout";
import { AddChatStep, type InputTab, type LoadedFile } from "./steps/AddChatStep";
import { DetailsStep, type ChatSummary } from "./steps/DetailsStep";
import { ResultStep, type Outcome } from "./steps/ResultStep";
import styles from "./App.module.css";

export default function App() {
  const [step, setStep] = useState<Step>(1);
  const [tab, setTab] = useState<InputTab>("upload");
  const [file, setFile] = useState<LoadedFile | null>(null);
  const [text, setText] = useState("");
  const [source, setSource] = useState<Source>("plain");
  const [outcome, setOutcome] = useState<Outcome>({ state: "loading" });
  const [mock, setMock] = useState(false);
  const request = useRef<AbortController | null>(null);
  const guessedFrom = useRef<string | null>(null);
  const main = useRef<HTMLElement>(null);
  const firstRender = useRef(true);

  useEffect(() => {
    const controller = new AbortController();
    getHealth(controller.signal)
      .then((h) => setMock(h.mock))
      .catch(() => {}); // the analyse step reports connection problems
    return () => controller.abort();
  }, []);

  // Move focus to the new step's heading so keyboard and screen reader users follow along.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    main.current?.querySelector<HTMLElement>("[data-step-heading]")?.focus();
  }, [step, outcome.state]);

  const chatText = tab === "upload" ? (file?.text ?? "") : text;
  const summary: ChatSummary =
    tab === "upload" && file
      ? { kind: "file", label: `${file.file.name}, ${plural(file.messages, "message", "messages")}` }
      : { kind: "text", label: `Pasted text, ${formatCount(text.length)} characters` };

  function goToDetails() {
    // Suggest a source from the text, but keep the user's choice if the chat has not changed.
    if (guessedFrom.current !== chatText) {
      setSource(guessSource(chatText));
      guessedFrom.current = chatText;
    }
    setStep(2);
  }

  async function runAnalysis() {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setStep(3);
    setOutcome({ state: "loading" });
    try {
      const input = tab === "upload" && file ? { file: file.file, source } : { text, source };
      const result = await analyze(input, controller.signal);
      if (!controller.signal.aborted) setOutcome({ state: "done", result });
    } catch (err) {
      if (controller.signal.aborted) return; // cancelled by the user
      const status = err instanceof ApiError ? err.status : 0;
      const detail = err instanceof ApiError ? err.detail : "";
      setOutcome({ state: "error", status, detail });
    }
  }

  function cancel() {
    request.current?.abort();
    setStep(2);
  }

  function restart() {
    request.current?.abort();
    setFile(null);
    setText("");
    setTab("upload");
    guessedFrom.current = null;
    setStep(1);
  }

  return (
    <div className={styles.page}>
      {mock && <MockBanner />}
      <main ref={main} className={styles.main}>
        <TopBar />
        <div className={styles.intro}>
          <Hero illustrated={step === 1} />
        </div>
        <div className={styles.flow}>
          {step === 1 && (
            <AddChatStep
              tab={tab}
              onTab={setTab}
              file={file}
              onFile={setFile}
              text={text}
              onText={setText}
              onNext={goToDetails}
            />
          )}
          {step === 2 && (
            <DetailsStep
              source={source}
              onSource={setSource}
              summary={summary}
              onBack={() => setStep(1)}
              onAnalyse={runAnalysis}
            />
          )}
          {step === 3 && (
            <ResultStep
              outcome={outcome}
              onCancel={cancel}
              onBack={() => setStep(2)}
              onRetry={runAnalysis}
              onRestart={restart}
            />
          )}
        </div>
      </main>
      <StepBar current={step} onGo={setStep} locked={step === 3 && outcome.state === "loading"} />
      <Footer />
    </div>
  );
}
