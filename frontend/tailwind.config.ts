import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark terminal / Bloomberg-inspired palette
        surface: {
          DEFAULT: "#0a0e1a",
          1: "#0f1525",
          2: "#141b2d",
          3: "#1a2238",
          4: "#202b45",
          border: "#2a3a5c",
        },
        accent: {
          blue: "#3b82f6",
          cyan: "#06b6d4",
          green: "#22c55e",
          red: "#ef4444",
          amber: "#f59e0b",
          purple: "#a855f7",
          orange: "#f97316",
        },
        text: {
          primary: "#e2e8f0",
          secondary: "#94a3b8",
          muted: "#475569",
          inverse: "#0a0e1a",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "ui-monospace", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.3s ease-in-out",
        "slide-up": "slideUp 0.3s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { transform: "translateY(10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
