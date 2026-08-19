import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/static/web/",
  plugins: [react()],
  build: {
    outDir: "../../backend/webapp/static/web",
    emptyOutDir: true,
    manifest: true,
  },
});
