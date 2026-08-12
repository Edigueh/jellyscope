import type { JSX } from "preact";
import { state } from "../state";
import * as ctl from "../controller";
import { Btn, Cluster, Divider, Segmented, Select } from "./ui";

const COLORSCALES = ["Viridis", "Inferno", "Plasma", "Cividis", "Hot", "Greys"];
const STRETCHES: { value: string; label: string }[] = [
  { value: "lupton_asinh", label: "Asinh (Lupton)" },
  { value: "log", label: "Log" },
];
const RGB_METHODS: { value: string; label: string }[] = [
  { value: "percentile_asinh", label: "Percentile Asinh" },
  { value: "lupton", label: "Lupton" },
];

// Display-only friendly datacube labels; option value stays the raw key.
function datacubeLabel(key: string): string {
  if (key === "nircam") return "Raw";
  if (key === "nircam_matched") return "PSF-matched";
  return key;
}

function filterLabel(): string {
  if (state.viewMode === "rgb") {
    return `R ${state.filters[state.rgbR]} · G ${state.filters[state.rgbG]} · B ${state.filters[state.rgbB]}`;
  }
  const name = state.filters[state.channel];
  const wl = state.wavelengths[name];
  return wl ? `${name} · ${wl.toFixed(3)} µm` : name;
}

function RgbChannelSelect(props: { anchor: "R" | "G" | "B"; index: number }): JSX.Element {
  return (
    <Select
      aria-label={`${props.anchor} channel`}
      value={String(props.index)}
      onChange={(e) =>
        ctl.setRgbChannel(props.anchor, Number((e.target as HTMLSelectElement).value))
      }
    >
      {state.filters.map((name, i) => {
        const wl = state.wavelengths[name];
        return (
          <option key={i} value={i}>
            {wl ? `${name} (${wl} µm)` : name}
          </option>
        );
      })}
    </Select>
  );
}

export function Toolbar(): JSX.Element {
  return (
    <div class="glass pointer-events-auto flex max-w-[calc(100vw-2rem)] flex-wrap items-center gap-x-3 gap-y-2 rounded-xl px-3 py-2 shadow-lg shadow-black/30">
      {/* Wordmark (header dissolved into the toolbar) */}
      <div class="flex items-center gap-2 pr-1">
        <span aria-hidden="true" class="text-accent text-md leading-none">
          ✦
        </span>
        <span class="text-md font-semibold tracking-tight text-ink">Jellyscope</span>
      </div>

      <Divider />

      <Cluster label="Source">
        <Select
          aria-label="Dataset"
          value={state.dataset}
          onChange={(e) => ctl.setDataset((e.target as HTMLSelectElement).value)}
        >
          {datasetOptions()}
        </Select>
        <Select
          aria-label="Datacube"
          value={state.datacube}
          onChange={(e) => ctl.setDatacube((e.target as HTMLSelectElement).value)}
        >
          {datacubeOptions()}
        </Select>
      </Cluster>

      <Divider />

      <Cluster label="View">
        <Segmented
          value={state.viewMode}
          onChange={(v) => ctl.setViewMode(v)}
          options={[
            { value: "single", label: "Single", title: "Single-band heatmap (S)" },
            { value: "rgb", label: "RGB", title: "RGB composite (R)" },
          ]}
        />
        {state.viewMode === "single" ? (
          <div class="flex items-center gap-2">
            <input
              type="range"
              aria-label="Filter channel"
              class="w-28 accent-accent"
              min={0}
              max={Math.max(0, state.filters.length - 1)}
              step={1}
              value={state.channel}
              onInput={(e) => ctl.setChannel(Number((e.target as HTMLInputElement).value))}
            />
            <Select
              aria-label="Colorscale"
              value={state.colorscale}
              onChange={(e) => ctl.setColorscale((e.target as HTMLSelectElement).value)}
            >
              {COLORSCALES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
            <Select
              aria-label="Stretch"
              value={state.stretch}
              onChange={(e) => ctl.setStretch((e.target as HTMLSelectElement).value)}
            >
              {STRETCHES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </Select>
          </div>
        ) : (
          <div class="flex items-center gap-2">
            <Select
              aria-label="RGB method"
              value={state.rgbMethod}
              onChange={(e) => ctl.setRgbMethod((e.target as HTMLSelectElement).value)}
            >
              {RGB_METHODS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </Select>
            <RgbChannelSelect anchor="R" index={state.rgbR} />
            <RgbChannelSelect anchor="G" index={state.rgbG} />
            <RgbChannelSelect anchor="B" index={state.rgbB} />
            {state.rgbMethod === "lupton" && (
              <label class="flex items-center gap-1.5 text-sm text-ink-dim">
                Q
                <input
                  type="range"
                  aria-label="Softening Q"
                  class="w-20 accent-accent"
                  min={1}
                  max={30}
                  step={0.5}
                  value={state.rgbQ}
                  onInput={(e) => ctl.setRgbQ(Number((e.target as HTMLInputElement).value))}
                />
                <span class="tabular w-8 text-accent">{state.rgbQ.toFixed(1)}</span>
              </label>
            )}
          </div>
        )}
        <span class="tabular text-sm text-accent">{filterLabel()}</span>
      </Cluster>

      <Divider />

      <Cluster label="Tools">
        <Segmented
          value={state.dragmode}
          onChange={(v) => ctl.setDragMode(v)}
          options={[
            { value: "pan", label: "Pan", title: "Pan / click to select clump (P)" },
            { value: "select", label: "Rect", title: "Rectangle select (T)" },
            { value: "lasso", label: "Lasso", title: "Lasso select (L)" },
          ]}
        />
      </Cluster>

      <Divider />

      <Cluster label="Overlays">
        <Btn active={state.showCentroids} onClick={() => ctl.toggleCentroids()} title="Centroids (C)">
          Centroids
        </Btn>
        <Btn
          active={state.showBoundaries}
          onClick={() => ctl.toggleBoundaries()}
          title="Boundaries (B)"
        >
          Boundaries
        </Btn>
      </Cluster>
    </div>
  );
}

// Dataset / datacube option lists. Datasets are fixed (from bootstrap);
// datacubes live in reactive state (setDataset refreshes them).
import { readBootstrap } from "../bootstrap";
const boot = readBootstrap();

function datasetOptions(): JSX.Element[] {
  return boot.datasets.map((d) => (
    <option key={d} value={d}>
      {d}
    </option>
  ));
}

function datacubeOptions(): JSX.Element[] {
  return state.datacubes.map((d) => (
    <option key={d} value={d}>
      {datacubeLabel(d)}
    </option>
  ));
}
