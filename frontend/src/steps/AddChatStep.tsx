import { ArrowRight, ClipboardText, UploadSimple } from "@phosphor-icons/react";
import { useId, useRef, useState } from "react";
import { MAX_BYTES, byteLength, countMessages, readFileText } from "../chat";
import { ChangeFileButton, DropZone, FieldError, FileInput, FileRow, PasteBox } from "../components/ChatInput";
import { Tabs, type TabItem } from "../components/Tabs";
import ui from "../components/ui.module.css";

export type InputTab = "upload" | "paste";

export interface LoadedFile {
  file: File;
  text: string;
  messages: number;
}

const TABS: TabItem<InputTab>[] = [
  { id: "upload", label: "Upload chat", icon: UploadSimple },
  { id: "paste", label: "Paste text", icon: ClipboardText },
];

interface Props {
  tab: InputTab;
  onTab: (tab: InputTab) => void;
  file: LoadedFile | null;
  onFile: (file: LoadedFile | null) => void;
  text: string;
  onText: (text: string) => void;
  onNext: () => void;
}

export function AddChatStep({ tab, onTab, file, onFile, text, onText, onNext }: Props) {
  const [fileError, setFileError] = useState<string | null>(null);
  const inputId = useId();
  const errorId = useId();
  const input = useRef<HTMLInputElement>(null);

  async function acceptFile(f: File) {
    setFileError(null);
    if (!f.name.toLowerCase().endsWith(".txt")) return setFileError("Only .txt files are supported.");
    if (f.size > MAX_BYTES) return setFileError("This file is larger than 1 MB. Try a shorter chat.");
    if (f.size === 0) return setFileError("This file is empty.");
    try {
      const content = await readFileText(f);
      onFile({ file: f, text: content, messages: countMessages(content) });
    } catch {
      setFileError("We could not read this file. Save it as plain UTF-8 text and try again.");
    }
  }

  const pasteReady = text.trim() !== "" && byteLength(text) <= MAX_BYTES;

  const nextButton = (enabled: boolean) => (
    <button type="button" className={`${ui.textButton} ${ui.actionsEnd}`} disabled={!enabled} onClick={onNext}>
      Next step
      <ArrowRight size={18} aria-hidden="true" />
    </button>
  );

  return (
    <section aria-labelledby="step-heading">
      <h2 id="step-heading" className="visually-hidden" tabIndex={-1} data-step-heading>
        Step 1: Add chat
      </h2>
      <Tabs label="How to add the chat" items={TABS} value={tab} onChange={onTab}>
        {tab === "upload" && (
          <>
            <FileInput
              ref={input}
              id={inputId}
              onFile={acceptFile}
              describedBy={fileError ? errorId : undefined}
            />
            {file ? (
              <div className={ui.card}>
                <FileRow
                  name={file.file.name}
                  size={file.file.size}
                  messages={file.messages}
                  onRemove={() => onFile(null)}
                />
                <div className={ui.actions}>
                  <ChangeFileButton onClick={() => input.current?.click()} />
                  {nextButton(true)}
                </div>
              </div>
            ) : (
              <DropZone inputId={inputId} onFile={acceptFile} />
            )}
            {fileError && <FieldError id={errorId}>{fileError}</FieldError>}
            {!file && (
              <p className={ui.hint} style={{ marginTop: 16, textAlign: "center" }}>
                WhatsApp: open the chat, then More, Export chat, Without media. A .txt file up to 1 MB.
              </p>
            )}
          </>
        )}
        {tab === "paste" && (
          <div className={ui.card}>
            <PasteBox value={text} onChange={onText} />
            <div className={ui.actions}>
              {!pasteReady && <p className={ui.hint}>Add a chat to continue.</p>}
              {nextButton(pasteReady)}
            </div>
          </div>
        )}
      </Tabs>
      <p className={ui.hint} style={{ marginTop: 12, textAlign: "center" }}>
        Image upload: planned for a later version.
      </p>
    </section>
  );
}
