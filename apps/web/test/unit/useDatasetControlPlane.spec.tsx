import React from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Dataset } from "@/src/entities/dataset/model";
import { useDatasetControlPlane } from "@/src/features/dataset-control-plane/useDatasetControlPlane";

const datasetHooks = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
  useDatasetsQuery: vi.fn(),
  useCreateDatasetMutation: vi.fn()
}));

vi.mock("@/src/entities/dataset/query", () => ({
  useDatasetsQuery: datasetHooks.useDatasetsQuery,
  useCreateDatasetMutation: datasetHooks.useCreateDatasetMutation
}));

function buildDataset(name: string, rows: Dataset["rows"]): Dataset {
  return {
    name,
    description: `${name} description`,
    source: `${name}-source`,
    createdAt: "2026-04-08T00:00:00Z",
    currentVersionId: `${name}-version-id`,
    version: `${name}-version`,
    rows,
    versions: [
      {
        datasetVersionId: `${name}-version-id`,
        datasetName: name,
        version: `${name}-version`,
        createdAt: "2026-04-08T00:00:00Z",
        rowCount: rows.length,
        rows
      }
    ]
  };
}

describe("useDatasetControlPlane", () => {
  let datasetsData: Dataset[];

  beforeEach(() => {
    datasetsData = [];
    datasetHooks.mutateAsync.mockReset();
    datasetHooks.useDatasetsQuery.mockImplementation(() => ({
      data: datasetsData,
      isPending: false,
      isError: false
    }));
    datasetHooks.useCreateDatasetMutation.mockReturnValue({
      mutateAsync: datasetHooks.mutateAsync,
      isPending: false
    });
  });

  it("auto-selects the first dataset when data loads", async () => {
    const { result, rerender } = renderHook(() => useDatasetControlPlane());

    expect(result.current.selectedDataset).toBe("");

    datasetsData = [
      buildDataset("crm-v2", [{ sampleId: "sample-1", input: "where is my order?", tags: ["shipping"], slice: "shipping", source: "crm" }]),
      buildDataset("returns-v3", [{ sampleId: "sample-2", input: "cancel my order", tags: ["returns"], slice: "returns", source: "crm" }])
    ];

    rerender();

    await waitFor(() => expect(result.current.selectedDataset).toBe("crm-v2"));
  });

  it("resets slice, tag, and source filters when the selected dataset changes", async () => {
    datasetsData = [
      buildDataset("crm-v2", [{ sampleId: "sample-1", input: "where is my order?", tags: ["shipping"], slice: "shipping", source: "crm" }]),
      buildDataset("returns-v3", [{ sampleId: "sample-2", input: "cancel my order", tags: ["returns"], slice: "returns", source: "support" }])
    ];

    const { result } = renderHook(() => useDatasetControlPlane());

    await waitFor(() => expect(result.current.selectedDataset).toBe("crm-v2"));

    act(() => {
      result.current.setSliceFilter("shipping");
      result.current.setTagFilter("shipping");
      result.current.setSourceFilter("crm");
    });

    expect(result.current.sliceFilter).toBe("shipping");
    expect(result.current.tagFilter).toBe("shipping");
    expect(result.current.sourceFilter).toBe("crm");

    act(() => {
      result.current.setSelectedDataset("returns-v3");
    });

    await waitFor(() => {
      expect(result.current.sliceFilter).toBe("");
      expect(result.current.tagFilter).toBe("");
      expect(result.current.sourceFilter).toBe("");
    });
  });

  it("stages JSONL uploads and only infers the dataset name when the field is empty", async () => {
    const { result } = renderHook(() => useDatasetControlPlane());

    const firstInput = document.createElement("input");
    const firstFile = new File(['{"input":"hello"}\n'], "support-regression.jsonl", { type: "application/json" });
    Object.defineProperty(firstInput, "files", { value: [firstFile] });

    await act(async () => {
      await result.current.handleDatasetUpload({ target: firstInput } as React.ChangeEvent<HTMLInputElement>);
    });

    expect(result.current.datasetName).toBe("support-regression");
    expect(result.current.pendingUpload).toEqual({
      fileName: "support-regression.jsonl",
      rows: [
        {
          sampleId: "sample-1",
          input: "hello",
          expected: null,
          tags: [],
          slice: null,
          source: null,
          metadata: null,
          exportEligible: null
        }
      ]
    });

    act(() => {
      result.current.setDatasetName("keep-existing-name");
    });

    const secondInput = document.createElement("input");
    const secondFile = new File(['{"input":"hello again"}\n'], "ignored-name.jsonl", { type: "application/json" });
    Object.defineProperty(secondInput, "files", { value: [secondFile] });

    await act(async () => {
      await result.current.handleDatasetUpload({ target: secondInput } as React.ChangeEvent<HTMLInputElement>);
    });

    expect(result.current.datasetName).toBe("keep-existing-name");
    expect(result.current.pendingUpload?.fileName).toBe("ignored-name.jsonl");
  });

  it("submits trimmed metadata and clears staged import state after a successful import", async () => {
    datasetHooks.mutateAsync.mockResolvedValue({
      name: "returns-review",
      currentVersionId: "dataset-version-returns-review",
      rows: [{ sampleId: "sample-1", input: "review order return" }]
    });

    const { result } = renderHook(() => useDatasetControlPlane());

    const uploadInput = document.createElement("input");
    const uploadFile = new File(['{"input":"review order return"}\n'], "returns-review.jsonl", { type: "application/json" });
    Object.defineProperty(uploadInput, "files", { value: [uploadFile] });

    await act(async () => {
      await result.current.handleDatasetUpload({ target: uploadInput } as React.ChangeEvent<HTMLInputElement>);
    });

    act(() => {
      result.current.setDatasetName(" returns-review ");
      result.current.setDatasetDescription(" High-value failures ");
      result.current.setDatasetSource(" support_ticket_backfill ");
      result.current.setDatasetVersion(" 2026-03-rl-v1 ");
    });

    await act(async () => {
      await result.current.handleImportPendingUpload();
    });

    expect(datasetHooks.mutateAsync).toHaveBeenCalledWith({
      name: "returns-review",
      description: "High-value failures",
      source: "support_ticket_backfill",
      version: "2026-03-rl-v1",
      rows: [
        expect.objectContaining({
          sampleId: "sample-1",
          input: "review order return"
        })
      ]
    });

    await waitFor(() => {
      expect(result.current.pendingUpload).toBeNull();
      expect(result.current.datasetName).toBe("");
      expect(result.current.datasetDescription).toBe("");
      expect(result.current.datasetSource).toBe("");
      expect(result.current.datasetVersion).toBe("");
      expect(result.current.latestImportedDatasetVersionId).toBe("dataset-version-returns-review");
    });
  });

  it("derives option lists and filtered preview rows from slice, tag, and source selections", async () => {
    datasetsData = [
      buildDataset("crm-v2", [
        {
          sampleId: "sample-1",
          input: "where is my order?",
          tags: ["shipping", "priority"],
          slice: "shipping",
          source: "crm",
          exportEligible: true
        },
        {
          sampleId: "sample-2",
          input: "cancel my order",
          tags: ["returns"],
          slice: "returns",
          source: "support",
          exportEligible: false
        }
      ])
    ];

    const { result } = renderHook(() => useDatasetControlPlane());

    await waitFor(() => expect(result.current.selectedDataset).toBe("crm-v2"));

    expect(result.current.sliceOptions).toEqual(["returns", "shipping"]);
    expect(result.current.tagOptions).toEqual(["priority", "returns", "shipping"]);
    expect(result.current.sourceOptions).toEqual(["crm", "support"]);

    act(() => {
      result.current.setSliceFilter("shipping");
      result.current.setTagFilter("priority");
      result.current.setSourceFilter("crm");
    });

    expect(result.current.filteredRows).toHaveLength(1);
    expect(result.current.previewRows).toHaveLength(1);
    expect(result.current.previewRows[0]?.sampleId).toBe("sample-1");
  });
});
