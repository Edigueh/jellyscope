// Keyboard shortcuts (latent UX win). Ignores keystrokes while typing in a
// form control. Returns a teardown fn.
import { state } from "./state";
import * as ctl from "./controller";

function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA" || el.isContentEditable;
}

export function setupKeyboard(): () => void {
  const onKey = (e: KeyboardEvent): void => {
    if (isTyping(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;
    switch (e.key.toLowerCase()) {
      case "s":
        void ctl.setViewMode("single");
        break;
      case "r":
        void ctl.setViewMode("rgb");
        break;
      case "p":
        ctl.setDragMode("pan");
        break;
      case "t":
        ctl.setDragMode("select");
        break;
      case "l":
        ctl.setDragMode("lasso");
        break;
      case "c":
        ctl.toggleCentroids();
        break;
      case "b":
        ctl.toggleBoundaries();
        break;
      case "[":
      case "]":
        ctl.toggleRail();
        break;
      case "arrowleft":
        if (state.viewMode === "single" && state.channel > 0) {
          e.preventDefault();
          void ctl.setChannel(state.channel - 1);
        }
        break;
      case "arrowright":
        if (state.viewMode === "single" && state.channel < state.filters.length - 1) {
          e.preventDefault();
          void ctl.setChannel(state.channel + 1);
        }
        break;
    }
  };
  globalThis.addEventListener("keydown", onKey);
  return () => globalThis.removeEventListener("keydown", onKey);
}
