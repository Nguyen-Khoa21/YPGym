import { defineConfig } from "@playwright/test";

// Minimal config for the member dashboard check. It expects the web app on WEB_URL
// (default http://localhost:5173) talking to a seeded demo backend on port 8001.
// Install a browser once with: npx playwright install chromium
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  use: { baseURL: process.env.WEB_URL ?? "http://localhost:5173", trace: "off" },
});
