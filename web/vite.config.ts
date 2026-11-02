import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Local development: run the Functions host on :7071 and use the
// Static Web Apps CLI (`npx swa start`) for sign-in emulation.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:7071" },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    chunkSizeWarningLimit: 2000,
  },
});
