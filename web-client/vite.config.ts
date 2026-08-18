import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: true,
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/web-auth": "http://localhost:8080",
      "/web-api": "http://localhost:8080",
      "/static": "http://localhost:8080",
    },
  },
});
