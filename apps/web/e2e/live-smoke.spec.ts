import { promises as fs } from "node:fs";
import { expect, test, type APIRequestContext, type Download } from "@playwright/test";

const liveE2E = process.env.AGENT_ATLAS_E2E_LIVE === "1";
const apiBaseUrl = process.env.AGENT_ATLAS_API_BASE_URL ?? "http://127.0.0.1:8005";

function apiUrl(path: string) {
  return `${apiBaseUrl}${path}`;
}

async function expectOkJson(request: APIRequestContext, path: string) {
  const response = await request.get(apiUrl(path));
  expect(response.ok(), `expected ${path} to succeed`).toBeTruthy();
  return response.json();
}

async function waitForExperimentToComplete(request: APIRequestContext, experimentId: string) {
  await expect
    .poll(
      async () => {
        const experiment = await expectOkJson(request, `/api/v1/experiments/${experimentId}`);
        return experiment.status;
      },
      {
        timeout: 6 * 60_000,
        intervals: [1_000, 2_000, 5_000]
      }
    )
    .toBe("completed");
}

async function waitForRunEvidence(request: APIRequestContext, experimentId: string) {
  await expect
    .poll(
      async () => {
        const runs = (await expectOkJson(request, `/api/v1/experiments/${experimentId}/runs`)) as Array<{
          trace_url?: string | null;
        }>;

        return {
          runCount: runs.length,
          hasTrace: runs.some((run) => Boolean(run.trace_url))
        };
      },
      {
        timeout: 6 * 60_000,
        intervals: [1_000, 2_000, 5_000]
      }
    )
    .toEqual({ runCount: 1, hasTrace: true });
}

function extractId(text: string, prefix: string) {
  const normalized = text.trim();
  if (!normalized.startsWith(prefix)) {
    throw new Error(`Expected "${normalized}" to start with "${prefix}"`);
  }
  return normalized.slice(prefix.length).replace(/\.$/, "").trim();
}

function requireText(value: string | null, label: string) {
  if (!value) {
    throw new Error(`Expected ${label} to contain text.`);
  }
  return value;
}

async function readDownload(download: Download) {
  const filePath = await download.path();
  if (!filePath) {
    throw new Error("Playwright did not persist the downloaded export file.");
  }
  return fs.readFile(filePath, "utf8");
}

test.describe("live product smoke", () => {
  test.skip(!liveE2E, "This regression only runs against the live stack.");
  test.setTimeout(10 * 60_000);

  test("agents, datasets, experiments, and exports complete the validated live loop", async ({
    page,
    request
  }) => {
    const suffix = `${Date.now()}`;
    const datasetName = `live-smoke-dataset-${suffix}`;
    const datasetVersion = `v-${suffix}`;
    const datasetSource = `playwright-live-${suffix}`;
    const sampleInput =
      'Inside the mounted project, edit `app.py` so `TARGET = "after"`. Do not modify any other file. After saving the change, reply exactly with `UPDATED app.py` and nothing else.';
    const expectedOutput = "UPDATED app.py";
    const sampleId = `${datasetName}-sample-1`;
    const datasetRows = `${JSON.stringify({
      sample_id: sampleId,
      input: sampleInput,
      expected: expectedOutput,
      tags: ["claude-code", "code-edit", "starter"],
      slice: "validated-code-edit-loop",
      source: datasetSource,
      export_eligible: true
    })}\n`;

    await page.goto("/agents");

    await expect(page.getByRole("heading", { name: "Agents" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Add an asset, review validation, then use ready assets" })).toBeVisible();

    await page.getByRole("button", { name: "Add Claude Code bridge" }).click();

    await expect(page.getByText("Claude Code Starter")).toBeVisible();
    await expect(page.getByText("Visible 1")).toBeVisible();
    await expect(page.getByText("Ready for experiments 1")).toBeVisible();
    await expect(page.getByRole("link", { name: /Create experiment/i })).toHaveAttribute(
      "href",
      "/experiments?agent=claude-code-starter"
    );

    await page.goto("/datasets");

    await expect(page.getByRole("heading", { name: "Datasets" })).toBeVisible();

    await page.getByLabel("Dataset name").fill(datasetName);
    await page.getByLabel("Version").fill(datasetVersion);
    await page.getByLabel("Source").fill(datasetSource);
    await page
      .getByLabel("Description")
      .fill("Playwright live smoke dataset for the validated four-page code-edit loop.");
    await page.getByLabel("Upload dataset JSONL").setInputFiles({
      name: `${datasetName}.jsonl`,
      mimeType: "application/x-ndjson",
      buffer: Buffer.from(datasetRows, "utf8")
    });

    await expect(page.getByText(`Imported dataset ${datasetName} with 1 sample.`)).toBeVisible();
    await expect(page.getByRole("link", { name: "Open imported dataset in experiments" })).toBeVisible();

    await page.getByRole("link", { name: "Open imported dataset in experiments" }).click();

    await expect(page).toHaveURL(new RegExp("/experiments\\?datasetVersion="));
    const datasetVersionId = new URL(page.url()).searchParams.get("datasetVersion");
    if (!datasetVersionId) {
      throw new Error("Expected datasetVersion handoff query param after dataset creation.");
    }
    await expect(page.getByRole("heading", { name: "Experiments" })).toBeVisible();
    await expect(page.getByLabel("Governed asset")).toHaveValue("claude-code-starter");
    await expect(page.getByRole("option", { name: `${datasetName} · Version ${datasetVersion}` })).toBeVisible();

    await page.getByRole("button", { name: "Create and start" }).click();

    const experimentMessage = page.locator("text=/Created and started experiment /").first();
    await expect(experimentMessage).toBeVisible();
    const experimentId = extractId(
      requireText(await experimentMessage.textContent(), "experiment creation message"),
      "Created and started experiment "
    );

    await waitForExperimentToComplete(request, experimentId);
    await waitForRunEvidence(request, experimentId);

    await page.goto(
      `/experiments?datasetVersion=${encodeURIComponent(datasetVersionId)}&experiment=${encodeURIComponent(experimentId)}`
    );

    await expect(page.getByRole("heading", { name: "Experiments" })).toBeVisible();
    await expect(page.getByText(sampleId)).toBeVisible();
    await expect(page.getByRole("link", { name: "Open Phoenix deeplink" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Open Phoenix" })).toBeVisible();

    await page.goto(`/exports?experiment=${encodeURIComponent(experimentId)}`);

    await expect(page.getByRole("heading", { name: "Exports" })).toBeVisible();
    await expect(page.getByLabel("Experiment")).toHaveValue(experimentId);
    await expect(page.getByText(`claude-code-starter on ${datasetName}`)).toBeVisible();

    await page.getByRole("button", { name: "Create export" }).click();

    const exportMessage = page.locator("text=/Created export /").first();
    await expect(exportMessage).toBeVisible();
    const exportId = extractId(requireText(await exportMessage.textContent(), "export creation message"), "Created export ");

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: "Download export" }).click();
    const download = await downloadPromise;
    const downloadContents = await readDownload(download);

    expect(download.suggestedFilename()).toContain(exportId);
    expect(downloadContents).toContain(sampleId);
    expect(downloadContents).toContain(sampleInput);
    expect(downloadContents).toContain(expectedOutput);
  });
});
