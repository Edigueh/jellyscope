import type { JSX } from "preact";
import { state } from "../state";
import { chrome } from "../controller";
import * as ctl from "../controller";
import type { ClumpDetailResponse } from "../types";

function Placeholder(props: { children: JSX.Element | string }): JSX.Element {
  return <p class="px-3 py-4 text-sm leading-relaxed text-ink-dim">{props.children}</p>;
}

function SectionTitle(props: { children: string; aside?: JSX.Element }): JSX.Element {
  return (
    <div class="sticky top-0 z-rail flex items-center justify-between border-b border-border bg-surface-1/95 px-3 py-2 backdrop-blur">
      <h2 class="text-md font-semibold tracking-tight text-ink">{props.children}</h2>
      {props.aside}
    </div>
  );
}

// Two-column property table shared by single-clump + used as a compare column.
function PropTable(props: { detail: ClumpDetailResponse }): JSX.Element {
  return (
    <table class="w-full border-collapse">
      <tbody>
        {props.detail.properties.entries.map((e) => (
          <tr key={e.label} class="border-b border-border/40 last:border-0">
            <td class="py-1 pr-2 text-sm text-ink-dim">{e.label}</td>
            <td class="tabular py-1 text-right text-sm text-ink">{e.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PropertiesPanel(): JSX.Element {
  const selected = state.selectedClumps;
  let body: JSX.Element;
  if (selected.size === 0) {
    body = chrome.coordReadout.includes("no clump") ? (
      <Placeholder>{chrome.coordReadout}</Placeholder>
    ) : (
      <Placeholder>Click a clump on the image or in the list to inspect its area, radius, and sky position.</Placeholder>
    );
  } else if (selected.size === 1 && chrome.detail) {
    body = <div class="px-3 py-2">{<PropTable detail={chrome.detail} />}</div>;
  } else {
    body = <CompareTable />;
  }
  return (
    <section class="border-b border-border">
      <SectionTitle>Properties</SectionTitle>
      {body}
    </section>
  );
}

// Multi-clump compare (latent win #3): columns = clumps, rows = property labels.
function CompareTable(): JSX.Element {
  const ids = Array.from(state.selectedClumps);
  const cols = ids.map((id) => chrome.compare.get(id)).filter(Boolean) as ClumpDetailResponse[];
  if (cols.length < 2) return <Placeholder>Loading comparison…</Placeholder>;
  const labels = cols[0].properties.entries.map((e) => e.label);
  return (
    <div class="overflow-x-auto px-3 py-2">
      <table class="w-full border-collapse text-sm">
        <thead>
          <tr class="border-b border-border">
            <th class="py-1 pr-2 text-left font-medium text-ink-dim">Property</th>
            {ids.map((id) => (
              <th key={id} class="tabular py-1 px-2 text-right font-medium text-accent">
                #{id}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {labels.map((label, r) => (
            <tr key={label} class="border-b border-border/40 last:border-0">
              <td class="py-1 pr-2 text-ink-dim">{label}</td>
              {cols.map((c, i) => (
                <td key={ids[i]} class="tabular py-1 px-2 text-right text-ink">
                  {c.properties.entries[r]?.value ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Angular separations (latent win #1) — shown when ≥2 clumps selected.
function SeparationsPanel(): JSX.Element {
  if (state.selectedClumps.size < 2) {
    return (
      <section class="border-b border-border">
        <SectionTitle>Separations</SectionTitle>
        <Placeholder>Select ≥2 clumps to measure their angular separations.</Placeholder>
      </section>
    );
  }
  let body: JSX.Element;
  if (chrome.separationsError) {
    body = <Placeholder>{chrome.separationsError}</Placeholder>;
  } else if (!chrome.separations) {
    body = <Placeholder>Loading separations…</Placeholder>;
  } else {
    const sel = state.selectedClumps;
    const pairs = chrome.separations.pairs.filter(
      (p) => sel.has(p.clump_a) && sel.has(p.clump_b),
    );
    if (pairs.length === 0) {
      body = <Placeholder>No pairs for the current selection.</Placeholder>;
    } else {
      body = (
        <table class="w-full border-collapse px-3 text-sm">
          <thead>
            <tr class="border-b border-border">
              <th class="py-1 pl-3 pr-2 text-left font-medium text-ink-dim">Pair</th>
              <th class="py-1 pr-2 text-right font-medium text-ink-dim">arcsec</th>
              {chrome.separations.pairs.some((p) => p.sep_pc != null) && (
                <th class="py-1 pr-3 text-right font-medium text-ink-dim">pc</th>
              )}
            </tr>
          </thead>
          <tbody>
            {pairs.map((p) => (
              <tr key={`${p.clump_a}-${p.clump_b}`} class="border-b border-border/40 last:border-0">
                <td class="tabular py-1 pl-3 pr-2 text-ink">
                  #{p.clump_a} · #{p.clump_b}
                </td>
                <td class="tabular py-1 pr-2 text-right text-ink">{p.sep_arcsec.toFixed(3)}</td>
                {chrome.separations!.pairs.some((q) => q.sep_pc != null) && (
                  <td class="tabular py-1 pr-3 text-right text-ink">
                    {p.sep_pc != null ? p.sep_pc.toFixed(1) : "—"}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
  }
  return (
    <section class="border-b border-border">
      <SectionTitle>Separations</SectionTitle>
      <div class="py-2">{body}</div>
    </section>
  );
}

function ClumpList(): JSX.Element {
  const filterSel = (
    <select
      aria-label="Filter clumps"
      value={chrome.clumpFilter}
      onChange={(e) => ctl.setClumpFilter((e.target as HTMLSelectElement).value)}
      class="h-6 rounded border border-border bg-surface-2 px-1.5 text-sm text-ink focus-visible:border-accent"
    >
      <option value="">All</option>
      <option value="disk">Disk</option>
      <option value="outside">Outside</option>
    </select>
  );
  return (
    <section class="flex min-h-0 flex-1 flex-col">
      <SectionTitle aside={filterSel}>Clumps</SectionTitle>
      <div class="min-h-0 flex-1 overflow-y-auto px-1.5 py-1.5">
        {chrome.clumps.length === 0 ? (
          <Placeholder>No clumps for this filter.</Placeholder>
        ) : (
          chrome.clumps.map((c) => {
            const isSel = state.selectedClumps.has(c.clump_id);
            const isDisk = c.component === "disk";
            return (
              <button
                key={c.clump_id}
                type="button"
                onClick={() => ctl.toggleClump(c.clump_id)}
                aria-pressed={isSel}
                class={
                  "flex w-full items-center gap-2 rounded-md px-2 py-1 text-left transition-colors duration-150 ease-out-quart focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent " +
                  (isSel ? "bg-accent-quiet" : "hover:bg-surface-2")
                }
              >
                <span
                  aria-hidden="true"
                  class={"h-1.5 w-1.5 shrink-0 rounded-full " + (isSel ? "bg-accent" : "bg-border")}
                />
                <span class="tabular text-sm text-ink">#{c.clump_id}</span>
                <span
                  class={
                    "rounded px-1.5 py-px text-xs " +
                    (isDisk
                      ? "text-disk ring-1 ring-inset ring-disk/50"
                      : "text-outside ring-1 ring-inset ring-outside/50")
                  }
                >
                  {c.component}
                </span>
                <span class="tabular ml-auto text-xs text-ink-dim">{c.area_pix} px</span>
              </button>
            );
          })
        )}
      </div>
    </section>
  );
}

export function RightRail(): JSX.Element {
  return (
    <div class="flex min-h-0 flex-1 flex-col">
      <PropertiesPanel />
      <SeparationsPanel />
      <ClumpList />
    </div>
  );
}
