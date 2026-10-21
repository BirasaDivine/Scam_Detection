import { FilePlus, Trash, UploadSimple, WarningCircle } from "@phosphor-icons/react";
import { forwardRef, useId, useState, type DragEvent } from "react";
import { MAX_BYTES, byteLength, formatCount, formatSize, plural } from "../chat";
import styles from "./ChatInput.module.css";
import ui from "./ui.module.css";

export function FieldError({ id, children }: { id?: string; children: string }) {
  return (
    <p id={id} className={ui.fieldError} role="alert">
      <WarningCircle size={18} aria-hidden="true" />
      {children}
    </p>
  );
}

interface FileInputProps {
  id: string;
  onFile: (file: File) => void;
  describedBy?: string;
}

/** Hidden file input shared by the drop zone and the "Change file" action. */
export const FileInput = forwardRef<HTMLInputElement, FileInputProps>(function FileInput(
  { id, onFile, describedBy },
  ref,
) {
  return (
    <input
      ref={ref}
      id={id}
      type="file"
      accept=".txt,text/plain"
      className={`visually-hidden ${styles.fileInput}`}
      aria-describedby={describedBy}
      onChange={(e) => {
        const file = e.target.files?.[0];
        if (file) onFile(file);
        e.target.value = ""; // allows choosing the same file again
      }}
    />
  );
});

function GhostCard() {
  return (
    <span className={styles.ghost} aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
  );
}

/** Strip with a dashed drop card in the middle and faded placeholder cards at the sides. */
export function DropZone({ inputId, onFile }: { inputId: string; onFile: (file: File) => void }) {
  const [dragging, setDragging] = useState(false);

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onFile(file);
  }

  return (
    <div className={styles.stage}>
      <GhostCard />
      <label
        htmlFor={inputId}
        className={styles.dropCard}
        data-dragging={dragging || undefined}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <UploadSimple size={24} aria-hidden="true" />
        <span>
          Attach a chat
          <br />
          by selecting
        </span>
      </label>
      <GhostCard />
    </div>
  );
}

/** Flat stack of sheets, like the folder in the reference, with the count on the front sheet. */
function FileStack({ messages, size }: { messages: number; size: number }) {
  const [value, unit] = formatSize(size);
  return (
    <span className={styles.stack} aria-hidden="true">
      <span className={styles.sheetBack} />
      <span className={styles.sheetMiddle} />
      <span className={styles.sheetFront}>
        <span>{plural(messages, "msg", "msgs")}</span>
        <span>
          {value}
          {unit}
        </span>
      </span>
    </span>
  );
}

interface FileRowProps {
  name: string;
  size: number;
  messages: number;
  onRemove: () => void;
}

export function FileRow({ name, size, messages, onRemove }: FileRowProps) {
  const [sizeValue, sizeUnit] = formatSize(size);
  return (
    <div className={styles.fileRow}>
      <FileStack messages={messages} size={size} />
      <div className={styles.fileMeta}>
        <p className={styles.fileName} title={name}>
          {name}
        </p>
        <p className={styles.fileDetails}>
          <span className={styles.accentText}>{plural(messages, "message", "messages")}</span>
          <span aria-hidden="true"> · </span>
          <span className={styles.nowrap}>
            <span className={ui.mono}>{sizeValue}</span>&nbsp;{sizeUnit}
          </span>
        </p>
      </div>
      <button
        type="button"
        className={`${ui.iconButton} ${styles.remove}`}
        onClick={onRemove}
        aria-label={`Remove ${name}`}
      >
        <Trash size={20} aria-hidden="true" />
      </button>
    </div>
  );
}

export function ChangeFileButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" className={ui.textButton} onClick={onClick}>
      <FilePlus size={20} aria-hidden="true" />
      Change file
    </button>
  );
}

export function PasteBox({ value, onChange }: { value: string; onChange: (text: string) => void }) {
  const id = useId();
  const hintId = useId();
  const countId = useId();
  const errorId = useId();
  const tooLong = byteLength(value) > MAX_BYTES;

  return (
    <div className={styles.paste}>
      <label htmlFor={id} className={styles.label}>
        Chat text
      </label>
      <p id={hintId} className={ui.hint}>
        Paste one message per line, or a single SMS.
      </p>
      <textarea
        id={id}
        className={styles.textarea}
        rows={7}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-describedby={`${hintId} ${countId}${tooLong ? ` ${errorId}` : ""}`}
        aria-invalid={tooLong || undefined}
        spellCheck={false}
      />
      <p id={countId} className={`${ui.hint} ${styles.counter}`}>
        <span className={ui.mono}>{formatCount(value.length)}</span> characters
      </p>
      {tooLong && <FieldError id={errorId}>This text is larger than 1 MB. Try a shorter chat.</FieldError>}
    </div>
  );
}
