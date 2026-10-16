import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: process.env.VITE_STATIC ? "./" : "/",
  build: { rollupOptions: { input: { customer: resolve(__dirname, "index.html"), console: resolve(__dirname, "console.html") } } },
  server: { port: 5173, proxy: { "/api": `http://127.0.0.1:${process.env.API_PORT ?? "8018"}` } },
});
