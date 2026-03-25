import { describe, expect, it } from "vitest";

import { runRecords, steps } from "./fixtures";

describe("fixture data sanity checks", () => {
  it("has baseline runs", () => {
    expect(runRecords.length).toBeGreaterThan(0);
  });

  it("run records contain valid status", () => {
    const values = new Set(runRecords.map((r) => r.status));
    expect(values.has("succeeded")).toBe(true);
    expect(values.has("failed")).toBe(true);
  });

  it("trajectory steps belong to a run", () => {
    const runIds = new Set(runRecords.map((r) => r.runId));
    for (const step of steps) {
      expect(runIds.has(step.runId)).toBe(true);
    }
  });
});
