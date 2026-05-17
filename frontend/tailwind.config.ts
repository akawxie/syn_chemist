import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0f14",
        panel: "#121822",
        border: "#1f2937",
        accent: "#22d3ee",
      },
    },
  },
  plugins: [],
};

export default config;
