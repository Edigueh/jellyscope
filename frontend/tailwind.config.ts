import type { Config } from "tailwindcss";

// Observatory palette — near-black slate, one restrained blue accent.
// Chrome must never compete with the scientific colormaps on the canvas.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "oklch(0.16 0.004 260)",
        "surface-1": "oklch(0.21 0.005 260)",
        "surface-2": "oklch(0.26 0.006 260)",
        border: "oklch(0.32 0.006 260)",
        ink: "oklch(0.93 0.004 260)",
        "ink-dim": "oklch(0.72 0.008 260)",
        accent: "oklch(0.70 0.15 250)",
        "accent-quiet": "oklch(0.70 0.15 250 / 0.15)",
        disk: "oklch(0.80 0.16 150)",
        outside: "oklch(0.80 0.14 75)",
        danger: "oklch(0.63 0.20 25)",
      },
      fontFamily: {
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
      },
      fontSize: {
        xs: ["0.6875rem", { lineHeight: "1rem" }],
        sm: ["0.75rem", { lineHeight: "1.1rem" }],
        base: ["0.8125rem", { lineHeight: "1.25rem" }],
        md: ["0.9375rem", { lineHeight: "1.4rem" }],
        lg: ["1.0625rem", { lineHeight: "1.5rem" }],
      },
      zIndex: {
        canvas: "0",
        overlay: "10",
        rail: "20",
        toolbar: "30",
        dropdown: "40",
      },
      transitionTimingFunction: {
        "out-quart": "cubic-bezier(0.25, 1, 0.5, 1)",
      },
    },
  },
  plugins: [],
} satisfies Config;
