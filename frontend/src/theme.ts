// Shared color constants — the single JS-side source of truth for overlay
// colors that MUST mirror image_viewer.py (_RED/_BLUE/_WHITE). If these change,
// change src/jellyscope/visualization/image_viewer.py:31-33 in lockstep or the
// client-side selection recolor will desync from the server-drawn figure.
export const CLUMP_COLOR = "#4a9eff"; // unselected boundary (accent) — mirror _BLUE
export const CLUMP_SELECTED_COLOR = "#ff5c5c"; // selected boundary (danger) — mirror _RED
export const CENTROID_COLOR = "#e8e8ea"; // centroid marker — mirror _WHITE
export const CLUMP_WIDTH = 1.2;
export const CLUMP_SELECTED_WIDTH = 2.5;
