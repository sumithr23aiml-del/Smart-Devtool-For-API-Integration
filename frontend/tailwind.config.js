/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        darkBg: "#09090B",
        darkCard: "#111827",
        primaryPurple: "#7C3AED",
        secondaryBlue: "#3B82F6",
        accentCyan: "#06B6D4",
        successGreen: "#22C55E",
        warningOrange: "#F59E0B",
        errorRed: "#EF4444",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
}
