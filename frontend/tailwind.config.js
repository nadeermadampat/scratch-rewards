/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Set per campaign from the client's brand (see lib/brand.ts).
        brand: "rgb(var(--brand) / <alpha-value>)",
        accent: "rgb(var(--accent) / <alpha-value>)",
        ink: "#0d0b1a",
      },
      fontFamily: {
        display: ['"Baloo 2"', "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        card: "0 24px 60px -18px rgb(0 0 0 / 0.65), 0 2px 0 0 rgb(255 255 255 / 0.08) inset",
        glow: "0 0 0 1px rgb(var(--accent) / 0.35), 0 12px 40px -8px rgb(var(--accent) / 0.45)",
      },
      keyframes: {
        sheen: { "0%": { transform: "translateX(-120%) skewX(-20deg)" }, "100%": { transform: "translateX(320%) skewX(-20deg)" } },
        floaty: { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-6px)" } },
        nudge: {
          "0%,100%": { transform: "translate(0,0) rotate(-8deg)" },
          "50%": { transform: "translate(46px,14px) rotate(6deg)" },
        },
      },
      animation: {
        sheen: "sheen 2.8s ease-in-out infinite",
        floaty: "floaty 3.5s ease-in-out infinite",
        nudge: "nudge 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
