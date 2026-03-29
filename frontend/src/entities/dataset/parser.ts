import type { DatasetRow } from "./model";

function normalizeDatasetTags(tags: unknown): string[] {
  if (!Array.isArray(tags)) {
    return [];
  }

  return tags.map((tag) => String(tag).trim()).filter(Boolean);
}

export function parseDatasetJsonl(content: string): DatasetRow[] {
  return content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const parsed = JSON.parse(line) as {
        sample_id?: unknown;
        input?: unknown;
        expected?: unknown;
        tags?: unknown;
        slice?: unknown;
        source?: unknown;
        metadata?: unknown;
        export_eligible?: unknown;
      };

      const input = typeof parsed.input === "string" ? parsed.input.trim() : "";
      if (!input) {
        throw new Error(`JSONL row ${index + 1} is missing a string input field.`);
      }

      const sampleId =
        typeof parsed.sample_id === "string" && parsed.sample_id.trim()
          ? parsed.sample_id.trim()
          : `sample-${index + 1}`;

      return {
        sampleId,
        input,
        expected: typeof parsed.expected === "string" ? parsed.expected : null,
        tags: normalizeDatasetTags(parsed.tags),
        slice: typeof parsed.slice === "string" ? parsed.slice : null,
        source: typeof parsed.source === "string" ? parsed.source : null,
        metadata:
          parsed.metadata && typeof parsed.metadata === "object" && !Array.isArray(parsed.metadata)
            ? (parsed.metadata as Record<string, unknown>)
            : null,
        exportEligible: typeof parsed.export_eligible === "boolean" ? parsed.export_eligible : null
      };
    });
}
