import { defineConfig } from "vite";
import preact from "@preact/preset-vite";
import { resolve } from "node:path";

// Served by FastAPI under /static/dist. base './' keeps asset URLs relative so
// they work behind the HF Space HTTPS proxy (no absolute http:// → mixed content).
export default defineConfig({
  base: "./",
  plugins: [preact()],
  build: {
    outDir: resolve(__dirname, "../src/jellyscope/web/static/dist"),
    emptyOutDir: true,
    manifest: true,
    // Plotly's full dist is ~4.7MB; it's one vendor chunk, not app bloat.
    chunkSizeWarningLimit: 5000,
    rollupOptions: {
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
