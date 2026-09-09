import { defineConfig } from "vite";
import preact from "@preact/preset-vite";
import { resolve } from "node:path";

// Two build targets:
//  - default (`vite build`): still emits into the FastAPI static dir for the
//    HF Space Docker deploy path. Keeps the manifest so the Jinja template
//    resolves hashed assets.
//  - static (`VITE_STATIC=1 vite build`): emits a standalone site to
//    <repo>/docs/ for GitHub Pages. index.html at docs/ is the entry.
const IS_STATIC = process.env.VITE_STATIC === "1";

export default defineConfig({
  base: "./",
  plugins: [preact()],
  build: {
    outDir: IS_STATIC
      ? resolve(__dirname, "../site")
      : resolve(__dirname, "../src/jellyscope/web/static/dist"),
    emptyOutDir: !IS_STATIC,
    manifest: !IS_STATIC,
    // Plotly's full dist is ~4.7MB; it's one vendor chunk, not app bloat.
    chunkSizeWarningLimit: 5000,
    rollupOptions: IS_STATIC
      ? {}
      : {
          input: resolve(__dirname, "src/main.tsx"),
        },
  },
  server: {
    port: 5173,
    strictPort: true,
    // Allow the FastAPI page (:5000) to pull modules/HMR from the dev server.
    cors: true,
  },
});
