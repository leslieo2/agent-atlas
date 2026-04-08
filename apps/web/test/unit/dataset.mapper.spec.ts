import { describe, expect, it } from "vitest";
import { mapDatasetRow, mapDatasetVersion, serializeDatasetRow } from "@/src/entities/dataset/mapper";

describe("dataset mappers", () => {
  it("maps API dataset rows into DatasetRow with null/default handling", () => {
    expect(
      mapDatasetRow({
        sample_id: "sample-1",
        input: "hello"
      })
    ).toEqual({
      sampleId: "sample-1",
      input: "hello",
      expected: null,
      tags: [],
      slice: null,
      source: null,
      metadata: null,
      exportEligible: null
    });
  });

  it("serializes DatasetRow into API create rows with null/default handling", () => {
    expect(
      serializeDatasetRow({
        sampleId: "sample-2",
        input: "world"
      })
    ).toEqual({
      sample_id: "sample-2",
      input: "world",
      expected: null,
      tags: [],
      slice: null,
      source: null,
      metadata: null,
      export_eligible: null
    });
  });

  it("maps dataset versions by reusing the shared row mapper", () => {
    expect(
      mapDatasetVersion({
        dataset_version_id: "dataset-version-1",
        dataset_name: "support-regression",
        version: null,
        created_at: "2026-04-08T00:00:00Z",
        row_count: 2,
        rows: [
          {
            sample_id: "sample-1",
            input: "hello",
            expected: "hi",
            tags: ["priority"],
            slice: "gold",
            source: "crm",
            metadata: { locale: "en-US" },
            export_eligible: true
          },
          {
            sample_id: "sample-2",
            input: "bye"
          }
        ]
      })
    ).toEqual({
      datasetVersionId: "dataset-version-1",
      datasetName: "support-regression",
      version: null,
      createdAt: "2026-04-08T00:00:00Z",
      rowCount: 2,
      rows: [
        {
          sampleId: "sample-1",
          input: "hello",
          expected: "hi",
          tags: ["priority"],
          slice: "gold",
          source: "crm",
          metadata: { locale: "en-US" },
          exportEligible: true
        },
        {
          sampleId: "sample-2",
          input: "bye",
          expected: null,
          tags: [],
          slice: null,
          source: null,
          metadata: null,
          exportEligible: null
        }
      ]
    });
  });
});
