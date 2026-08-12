// Self-check for the ported science-core pure functions. Run: `npm test`
// (node --test with native TS type-stripping, Node 22+). Guards the RGB
// wavelength logic and rect/lasso hit-testing against silent regressions.
import { test } from "node:test";
import assert from "node:assert/strict";
import { resolveRgbDefaults, captureRgbDeltas, snapRgbFromAnchor } from "../src/viewer/rgb.ts";
import { clumpsInSelection } from "../src/viewer/selection.ts";

test("resolveRgbDefaults picks named F200W/F115W/F090W when present", () => {
  const filters = ["F090W", "F115W", "F150W", "F200W"];
  const wl = { F090W: 0.9, F115W: 1.15, F150W: 1.5, F200W: 2.0 };
  const r = resolveRgbDefaults(filters, wl);
  assert.equal(filters[r.r], "F200W");
  assert.equal(filters[r.g], "F115W");
  assert.equal(filters[r.b], "F090W");
});

test("resolveRgbDefaults falls back to λ-rank when names absent", () => {
  const filters = ["A", "B", "C"];
  const wl = { A: 1.0, B: 2.0, C: 3.0 };
  const r = resolveRgbDefaults(filters, wl);
  assert.equal(filters[r.r], "C"); // max λ
  assert.equal(filters[r.b], "A"); // min λ
});

test("snapRgbFromAnchor keeps R>G>B wavelength ordering on anchor change", () => {
  const filters = ["F090W", "F115W", "F150W", "F200W", "F277W"];
  const wl = { F090W: 0.9, F115W: 1.15, F150W: 1.5, F200W: 2.0, F277W: 2.79 };
  const rgb = resolveRgbDefaults(filters, wl);
  const { deltaRG, deltaGB } = captureRgbDeltas(filters, wl, rgb);
  // Move the red anchor to F277W; G and B should snap to preserve the offsets.
  const moved = { ...rgb, r: filters.indexOf("F277W") };
  const snapped = snapRgbFromAnchor("R", filters, wl, moved, deltaRG, deltaGB);
  assert.ok(wl[filters[snapped.r]] > wl[filters[snapped.g]]);
  assert.ok(wl[filters[snapped.g]] > wl[filters[snapped.b]]);
});

test("clumpsInSelection returns centroids inside a rect range", () => {
  const centroids = [
    { clump_id: 1, x: 0.0, y: 0.0 },
    { clump_id: 2, x: 5.0, y: 5.0 },
    { clump_id: 3, x: -3.0, y: 2.0 },
  ];
  const ed = { range: { x: [-1, 1], y: [-1, 1] } };
  assert.deepEqual(clumpsInSelection(ed, centroids), [1]);
});

test("clumpsInSelection handles a lasso polygon", () => {
  const centroids = [
    { clump_id: 1, x: 0.5, y: 0.5 },
    { clump_id: 2, x: 9, y: 9 },
  ];
  const ed = { lassoPoints: { x: [0, 1, 1, 0], y: [0, 0, 1, 1] } };
  assert.deepEqual(clumpsInSelection(ed, centroids), [1]);
});
