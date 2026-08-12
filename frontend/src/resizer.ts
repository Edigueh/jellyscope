// Drag-to-resize the right rail. Ports the old sidebar resizer: writes
// --sidebar-w (clamped), calls onRelease to reflow Plotly. Returns teardown.
export function setupResizer(handle: HTMLElement, onRelease: () => void): () => void {
  let dragging = false;

  const onMove = (e: MouseEvent): void => {
    if (!dragging) return;
    const w = Math.max(260, Math.min(900, window.innerWidth - e.clientX));
    document.documentElement.style.setProperty("--sidebar-w", `${w}px`);
  };
  const onUp = (): void => {
    if (!dragging) return;
    dragging = false;
    handle.classList.remove("bg-accent");
    document.body.style.userSelect = "";
    onRelease();
  };
  const onDown = (e: MouseEvent): void => {
    dragging = true;
    handle.classList.add("bg-accent");
    document.body.style.userSelect = "none";
    e.preventDefault();
  };

  handle.addEventListener("mousedown", onDown);
  globalThis.addEventListener("mousemove", onMove);
  globalThis.addEventListener("mouseup", onUp);
  return () => {
    handle.removeEventListener("mousedown", onDown);
    globalThis.removeEventListener("mousemove", onMove);
    globalThis.removeEventListener("mouseup", onUp);
  };
}
