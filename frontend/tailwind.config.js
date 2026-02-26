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
        kasi: {
          green: "#059669",
          "green-light": "#10b981",
          orange: "#f97316",
          "orange-soft": "#fb923c",
        },
      },
    },
  },
  plugins: [],
}
