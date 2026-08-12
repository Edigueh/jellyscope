// Shared chrome primitives — one consistent vocabulary across the toolbar and
// rail. Every interactive element carries default/hover/focus-visible/disabled.
import type { ComponentChildren, JSX } from "preact";

// A labeled control group in the floating toolbar.
export function Cluster(props: {
  label: string;
  children: ComponentChildren;
}): JSX.Element {
  return (
    <div class="flex items-center gap-1.5">
      <span class="text-xs uppercase tracking-wide text-ink-dim/70 select-none">{props.label}</span>
      <div class="flex items-center gap-1">{props.children}</div>
    </div>
  );
}

export function Divider(): JSX.Element {
  return <div class="h-5 w-px bg-border/80" aria-hidden="true" />;
}

export function Select(props: JSX.IntrinsicElements["select"]): JSX.Element {
  const { class: cls, children, ...rest } = props;
  return (
    <select
      {...rest}
      class={
        "h-7 rounded-md border border-border bg-surface-2 px-2 text-sm text-ink " +
        "hover:border-ink-dim focus-visible:border-accent transition-colors " +
        "duration-150 ease-out-quart " +
        (cls ?? "")
      }
    >
      {children}
    </select>
  );
}

// A pressable button; `active` fills with accent (used for toggles + segments).
export function Btn(
  props: JSX.HTMLAttributes<HTMLButtonElement> & { active?: boolean },
): JSX.Element {
  const { class: cls, active, children, ...rest } = props;
  const base =
    "h-7 rounded-md border px-2.5 text-sm transition-colors duration-150 ease-out-quart " +
    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent ";
  const look = active
    ? "border-accent bg-accent text-bg font-medium "
    : "border-border bg-surface-2 text-ink-dim hover:border-ink-dim hover:text-ink ";
  return (
    <button type="button" {...rest} class={base + look + (cls ?? "")}>
      {children}
    </button>
  );
}

// A segmented control (Single/RGB, tools).
export function Segmented<T extends string>(props: {
  value: T;
  options: { value: T; label: string; title?: string }[];
  onChange: (v: T) => void;
}): JSX.Element {
  return (
    <div class="inline-flex rounded-md border border-border bg-surface-2 p-0.5" role="group">
      {props.options.map((o) => {
        const active = o.value === props.value;
        return (
          <button
            key={o.value}
            type="button"
            title={o.title}
            aria-pressed={active}
            onClick={() => props.onChange(o.value)}
            class={
              "h-6 rounded px-2.5 text-sm transition-colors duration-150 ease-out-quart " +
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent " +
              (active
                ? "bg-accent text-bg font-medium"
                : "text-ink-dim hover:text-ink")
            }
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
