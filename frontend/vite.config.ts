import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// В dev-режиме запросы /api проксируются на FastAPI (uvicorn на :8000)
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    allowedHosts: true,
    proxy: { "/api": "http://localhost:8000" },
  },
});
