import type { JSX } from "preact";
import { useEffect, useRef } from "preact/hooks";
import { state } from "../state";
import { chrome } from "../controller";
import * as ctl from "../controller";
import { useStore } from "../useStore";
import { Toolbar } from "./Toolbar";
import { RightRail } from "./RightRail";
import { initViewer, renderViewer, resizeViewer } from "../viewer/mountViewer";
import type { ClumpCentroid } from "../viewer/click";
import { setupResizer } from "../resizer";
import { setupKeyboard } from "../keyboard";

// Centroids in axis-space for rect/lasso hit-testing. Read from the live heatmap
// trace's x/y arrays via clump list x0/y0 (pixel indices → axis coords).
function clumpCentroids(): ClumpCentroid[] {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const el = document.getElementById("galaxy-viewer") as any;
  const heat = el?.data?.[0];
  const xArr: number[] | undefined = heat?.x;
  const yArr: number[] | undefined = heat?.y;
  return chrome.clumps.map((c) => ({
    clump_id: c.clump_id,
    // x0/y0 are pixel indices; map to axis coords if the heatmap carries arrays.
    x: Array.isArray(xArr) ? (xArr[Math.round(c.x0)] ?? c.x0) : c.x0,
    y: Array.isArray(yArr) ? (yArr[Math.round(c.y0)] ?? c.y0) : c.y0,
  }));
}

export function App(): JSX.Element {
  useStore();
  const canvasRef = useRef<HTMLDivElement>(null);
  const railRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    canvasRef.current.id = "galaxy-viewer";
    ctl.initRgb();
    initViewer(canvasRef.current, {
      onPixel: (x, y) => void ctl.handlePixel(x, y),
      onSelectClumps: (ids) => void ctl.selectClumps(ids),
      onHover: (r) => ctl.setCoordReadout(r),
      clumpCentroids,
    });
    void ctl.loadClumps();
    void renderViewer();
    const teardownKb = setupKeyboard();
    return teardownKb;
  }, []);

  return (
    <div class="relative flex h-full w-full overflow-hidden bg-bg">
      {/* Canvas column owns the floating chrome so it can never overlap the rail. */}
      <div class="relative min-w-0 flex-1">
        <div ref={canvasRef} class="h-full w-full" />

        {/* Floating toolbar (top-left), confined to the canvas column. */}
        <div class="pointer-events-none absolute inset-x-3 top-3 z-toolbar flex justify-start">
          <Toolbar />
        </div>

        {/* Coordinate readout (bottom-left), mono. */}
        <div
          aria-live="polite"
          class="glass tabular pointer-events-none absolute bottom-3 left-3 z-overlay min-h-[1.5rem] rounded-md px-2.5 py-1 text-sm text-ink-dim"
          style={{ opacity: chrome.coordReadout ? 1 : 0, transition: "opacity 150ms" }}
        >
          {chrome.coordReadout || "—"}
        </div>

        {/* Loading bar (top edge of the canvas) while a figure fetches. */}
        {chrome.loading && (
          <div class="absolute inset-x-0 top-0 z-dropdown h-0.5 overflow-hidden bg-transparent">
            <div class="h-full w-1/3 animate-[loading_1s_ease-in-out_infinite] bg-accent" />
          </div>
        )}
      </div>

      {/* Docked rail — a sibling of the canvas column, never under the float. */}
      {!state.railCollapsed && (
        <div ref={railRef} class="relative flex">
          <Resizer railRef={railRef} />
          <div
            class="flex h-full flex-col border-l border-border bg-surface-1"
            style={{ width: "var(--sidebar-w, 380px)" }}
          >
            {/* Rail header: title + collapse control. */}
            <div class="flex items-center justify-between border-b border-border px-3 py-2">
              <span class="text-xs uppercase tracking-wide text-ink-dim/70">Inspector</span>
              <button
                type="button"
                onClick={() => ctl.toggleRail()}
                title="Hide panels (])"
                aria-label="Hide panels"
                class="flex h-6 w-6 items-center justify-center rounded text-ink-dim hover:bg-surface-2 hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
              >
                ›
              </button>
            </div>
            <RightRail />
          </div>
        </div>
      )}

      {/* When collapsed, a floating tab brings the rail back (pinned to viewport). */}
      {state.railCollapsed && (
        <button
          type="button"
          onClick={() => ctl.toggleRail()}
          title="Show panels (])"
          aria-label="Show panels"
          class="glass pointer-events-auto absolute right-3 top-3 z-toolbar flex h-8 w-8 items-center justify-center rounded-lg text-ink-dim hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          ‹
        </button>
      )}
    </div>
  );
}

// Drag handle on the rail's left edge; writes --sidebar-w, reflows Plotly on release.
function Resizer(props: { railRef: preact.RefObject<HTMLDivElement> }): JSX.Element {
  const handleRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (handleRef.current) return setupResizer(handleRef.current, () => resizeViewer());
  }, []);
  void props;
  return (
    <div
      ref={handleRef}
      role="separator"
      aria-orientation="vertical"
      title="Drag to resize"
      class="z-rail w-1 cursor-col-resize bg-border transition-colors hover:bg-accent"
    />
  );
}
