import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as datasetApi from "@/src/entities/dataset/api";
import { renderWithQueryClient } from "@/test/setup";
import DatasetsWorkspace from "@/src/widgets/datasets-workspace/DatasetsWorkspace";

vi.mock("@/src/entities/dataset/api", () => ({
  listDatasets: vi.fn(),
  createDataset: vi.fn()
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

describe("Datasets workspace", () => {
  beforeEach(() => {
    (datasetApi.listDatasets as unknown as MockedApiFn).mockReset();
    (datasetApi.createDataset as unknown as MockedApiFn).mockReset();

    (datasetApi.listDatasets as unknown as MockedApiFn).mockResolvedValue([
      {
        name: "crm-v2",
        rows: [
          { sampleId: "sample-1", input: "where is my order?", expected: "status lookup", tags: ["shipping"] },
          { sampleId: "sample-2", input: "cancel my order", expected: null, tags: [] }
        ]
      }
    ]);
    (datasetApi.createDataset as unknown as MockedApiFn).mockResolvedValue({
      name: "crm-v2",
      rows: []
    });
  });

  it("loads the existing dataset catalog and preview", async () => {
    renderWithQueryClient(<DatasetsWorkspace />);

    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));

    expect(await screen.findByText("Datasets workspace")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /crm-v2/i })).toBeInTheDocument();
    expect(screen.getByText("where is my order?")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open in evals" })).toHaveAttribute("href", "/evals?dataset=crm-v2");
    expect(screen.getByRole("link", { name: "Open in playground" })).toHaveAttribute(
      "href",
      "/playground?dataset=crm-v2"
    );
  });

  it("uploads jsonl and refreshes the dataset list", async () => {
    (datasetApi.listDatasets as unknown as MockedApiFn)
      .mockResolvedValueOnce([])
      .mockResolvedValue([
        {
          name: "support-batch",
          rows: [
            { sampleId: "support-1", input: "where is my refund?", expected: null, tags: [] },
            { sampleId: "support-2", input: "cancel this order", expected: null, tags: [] }
          ]
        }
      ]);
    (datasetApi.createDataset as unknown as MockedApiFn).mockResolvedValue({
      name: "support-batch",
      rows: [
        { sampleId: "support-1", input: "where is my refund?", expected: null, tags: [] },
        { sampleId: "support-2", input: "cancel this order", expected: null, tags: [] }
      ]
    });

    renderWithQueryClient(<DatasetsWorkspace />);

    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByLabelText("Dataset name"), { target: { value: "support-batch" } });
    const file = new File(
      ['{"sample_id":"support-1","input":"where is my refund?"}\n{"sample_id":"support-2","input":"cancel this order"}\n'],
      "support-batch.jsonl",
      { type: "application/json" }
    );
    fireEvent.change(screen.getByLabelText("Upload dataset JSONL"), {
      target: { files: [file] }
    });

    await waitFor(() =>
      expect(datasetApi.createDataset).toHaveBeenCalledWith({
        name: "support-batch",
        rows: [
          { sampleId: "support-1", input: "where is my refund?", expected: null, tags: [] },
          { sampleId: "support-2", input: "cancel this order", expected: null, tags: [] }
        ]
      })
    );

    expect(await screen.findByText(/Imported dataset support-batch with 2 samples\./)).toBeInTheDocument();
    expect(screen.getByText("where is my refund?")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open imported dataset in evals" })).toHaveAttribute(
      "href",
      "/evals?dataset=support-batch"
    );
  });

  it("creates a manual single-sample dataset and selects it", async () => {
    (datasetApi.listDatasets as unknown as MockedApiFn)
      .mockResolvedValueOnce([])
      .mockResolvedValue([
        {
          name: "returns-review",
          rows: [
            {
              sampleId: "returns-review-sample-1",
              input: "review order return",
              expected: null,
              tags: []
            }
          ]
        }
      ]);
    (datasetApi.createDataset as unknown as MockedApiFn).mockResolvedValue({
      name: "returns-review",
      rows: [
        {
          sampleId: "returns-review-sample-1",
          input: "review order return",
          expected: null,
          tags: []
        }
      ]
    });

    renderWithQueryClient(<DatasetsWorkspace />);

    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByLabelText("Dataset name"), { target: { value: "returns-review" } });
    fireEvent.change(screen.getByLabelText("Sample input"), { target: { value: "review order return" } });
    fireEvent.click(screen.getByRole("button", { name: "Create dataset" }));

    await waitFor(() =>
      expect(datasetApi.createDataset).toHaveBeenCalledWith({
        name: "returns-review",
        rows: [
          {
            sampleId: "returns-review-sample-1",
            input: "review order return",
            expected: null,
            tags: []
          }
        ]
      })
    );

    expect(await screen.findByText(/Created dataset returns-review with 1 sample\./)).toBeInTheDocument();
    expect(screen.getByText("review order return")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open imported dataset in playground" })).toHaveAttribute(
      "href",
      "/playground?dataset=returns-review"
    );
  });
});
