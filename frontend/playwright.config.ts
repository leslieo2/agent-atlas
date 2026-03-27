import { defineConfig, devices } from "@playwright/test";

const liveE2E = process.env.AGENT_ATLAS_E2E_LIVE === "1";
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
const localNoProxyHosts = "127.0.0.1,localhost";

function appendNoProxy(value: string | undefined) {
  if (!value) {
    return localNoProxyHosts;
  }

  const entries = value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);

  for (const host of localNoProxyHosts.split(",")) {
    if (!entries.includes(host)) {
      entries.push(host);
    }
  }

  return entries.join(",");
}

process.env.NO_PROXY = appendNoProxy(process.env.NO_PROXY);
process.env.no_proxy = appendNoProxy(process.env.no_proxy);

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
          "/bin/zsh -lc 'NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost npm run dev -- --hostname 127.0.0.1 --port 3000'",
        url: "http://127.0.0.1:3000",
        reuseExistingServer: true,
        timeout: 120_000
      }
});
