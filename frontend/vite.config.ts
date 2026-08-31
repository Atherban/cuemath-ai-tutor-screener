import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      // No "/ws" proxy here on purpose: Vite's http-proxy does not handle
      // upstream WebSocket disconnects cleanly and floods the log with
      // EPIPE/ECONNRESET. The interview socket connects directly to the
      // backend via VITE_WS_BASE_URL (see .env.example).
    },
  },
});