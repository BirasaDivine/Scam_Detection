import type { Icon } from "@phosphor-icons/react";
import { useRef, type KeyboardEvent, type ReactNode } from "react";
import styles from "./Tabs.module.css";

export interface TabItem<T extends string> {
  id: T;
  label: string;
  icon: Icon;
}

interface TabsProps<T extends string> {
  label: string;
  items: TabItem<T>[];
  value: T;
  onChange: (id: T) => void;
  children: ReactNode;
}

export const tabId = (id: string) => `tab-${id}`;
export const panelId = (id: string) => `panel-${id}`;

/** ARIA tabs: arrow keys, Home and End move between tabs and select them. */
export function Tabs<T extends string>({ label, items, value, onChange, children }: TabsProps<T>) {
  const refs = useRef(new Map<T, HTMLButtonElement>());

  function onKeyDown(e: KeyboardEvent) {
    const i = items.findIndex((t) => t.id === value);
    const next = {
      ArrowRight: (i + 1) % items.length,
      ArrowLeft: (i - 1 + items.length) % items.length,
      Home: 0,
      End: items.length - 1,
    }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    const id = items[next].id;
    onChange(id);
    refs.current.get(id)?.focus();
  }

  return (
    <div>
      <div role="tablist" aria-label={label} className={styles.list} onKeyDown={onKeyDown}>
        {items.map(({ id, label: text, icon: TabIcon }) => {
          const selected = id === value;
          return (
            <button
              key={id}
              ref={(el) => {
                if (el) refs.current.set(id, el);
              }}
              type="button"
              role="tab"
              id={tabId(id)}
              aria-selected={selected}
              aria-controls={panelId(id)}
              tabIndex={selected ? 0 : -1}
              className={styles.tab}
              onClick={() => onChange(id)}
            >
              <TabIcon size={18} weight={selected ? "bold" : "regular"} aria-hidden="true" />
              {text}
            </button>
          );
        })}
      </div>
      <div role="tabpanel" id={panelId(value)} aria-labelledby={tabId(value)} className={styles.panel}>
        {children}
      </div>
    </div>
  );
}
