/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./sectionminer/server/templates/**/*.{html,js,ts}",
    "./sectionminer/server/static/**/*.{js,ts}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "system-ui",
          "sans-serif",
        ],
      },
      boxShadow: {
        soft: "0 10px 30px rgba(15, 23, 42, 0.06)",
      },
    },
  },
  plugins: [],
};
