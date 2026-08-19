import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    // Incident and authentication suites intentionally stub global fetch,
    // clipboard, and document cookies. Keep files sequential so one suite's
    // browser doubles cannot race another suite's async effects.
    fileParallelism: false,
    // Run at the path the app is actually served from. document.cookie only
    // exposes cookies whose Path is a prefix of the page's path, so testing at
    // "/" would hide a CSRF cookie the real workspace cannot read.
    environmentOptions: { jsdom: { url: "http://localhost/workspace" } },
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },
});
