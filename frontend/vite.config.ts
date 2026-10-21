import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

const sensitiveApiPattern = /^https?:\/\/[^/]+\/api(?:\/|$)/i;
const sensitiveApiMethods = ["GET", "POST", "PUT", "PATCH", "DELETE"] as const;

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      devOptions: { enabled: false },
      injectRegister: false,
      manifest: false,
      registerType: "prompt",
      workbox: {
        cleanupOutdatedCaches: true,
        globPatterns: ["**/*.{js,css,html,ico,png,svg,webmanifest}"],
        navigateFallback: "index.html",
        navigateFallbackDenylist: [/^\/api(?:\/|$)/],
        runtimeCaching: sensitiveApiMethods.map((method) => ({
          handler: "NetworkOnly",
          method,
          urlPattern: sensitiveApiPattern,
        })),
      },
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
});
