import { defineConfig, devices } from "@playwright/test";

const liveE2E = process.env.AFLIGHT_E2E_LIVE === "1";
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  retries: 0,
  fullyParallel: true,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    headless: true,
    trace: "on-first-retry",
    ...devices["Desktop Chrome"]
  },
  projects: [
    {
      name: "desktop-chrome",
      use: {
        ...devices["Desktop Chrome"]
      }
    }
  ],
  webServer: liveE2E
    ? undefined
    : {
        command:
          "/bin/zsh -lc 'NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3000'",
        url: "http://127.0.0.1:3000",
        reuseExistingServer: true,
        timeout: 120_000
      }
});
