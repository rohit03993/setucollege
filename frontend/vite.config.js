import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/ui/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/colleges": "http://127.0.0.1:8000",
      "/auth": "http://127.0.0.1:8000",
      "/students": "http://127.0.0.1:8000",
      "/team": "http://127.0.0.1:8000",
      "/assets": "http://127.0.0.1:8000"
    }
  },
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
