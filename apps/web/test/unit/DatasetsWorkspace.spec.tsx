import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DatasetsWorkspace from "@/src/widgets/datasets-workspace/DatasetsWorkspace";

const datasetHooks = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
  useDatasetsQuery: vi.fn(),
  useCreateDatasetMutation: vi.fn()
}));

vi.mock("@/src/entities/dataset/query", () => ({
  useDatasetsQuery: datasetHooks.useDatasetsQuery,
  useCreateDatasetMutation: datasetHooks.useCreateDatasetMutation
}));

describe("DatasetsWorkspace", () => {
  beforeEach(() => {
    datasetHooks.mutateAsync.mockReset();
    datasetHooks.useDatasetsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false
    });
    datasetHooks.useCreateDatasetMutation.mockReturnValue({
      mutateAsync: datasetHooks.mutateAsync,
      isPending: false
    });
  });

  it("stages the JSONL upload before import and infers the dataset name from the file", async () => {
    datasetHooks.mutateAsync.mockResolvedValue({
      name: "support-regression",
      currentVersionId: "dataset-version-1",
      rows: [{ sampleId: "sample-1", input: "hello" }]
    });

    render(<DatasetsWorkspace />);

    const file = new File(['{"input":"hello"}\n'], "support-regression.jsonl", { type: "application/json" });

    fireEvent.change(screen.getByLabelText("Upload dataset JSONL"), {
      target: { files: [file] }
    });

    await waitFor(() =>
      expect(screen.getByText(/Ready to import 1 sample from support-regression\.jsonl\./)).toBeInTheDocument()
    );

    expect(datasetHooks.mutateAsync).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Dataset name")).toHaveValue("support-regression");

    fireEvent.click(screen.getByRole("button", { name: "Import dataset" }));

    await waitFor(() =>
      expect(datasetHooks.mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "support-regression",
          description: null,
          source: null,
          version: null,
          rows: [expect.objectContaining({ sampleId: "sample-1", input: "hello" })]
        })
      )
    );
  });

  it("uses edited metadata when the staged upload is confirmed", async () => {
    datasetHooks.mutateAsync.mockResolvedValue({
      name: "customer-regressions",
      currentVersionId: "dataset-version-2",
      rows: [{ sampleId: "sample-1", input: "hello" }]
    });

    render(<DatasetsWorkspace />);

    fireEvent.change(screen.getByLabelText("Upload dataset JSONL"), {
      target: { files: [new File(['{"input":"hello"}\n'], "support-regression.jsonl", { type: "application/json" })] }
    });

    await waitFor(() => expect(screen.getByLabelText("Dataset name")).toHaveValue("support-regression"));

    fireEvent.change(screen.getByLabelText("Dataset name"), { target: { value: "customer-regressions" } });
    fireEvent.change(screen.getByLabelText("Version"), { target: { value: "2026-04-v1" } });
    fireEvent.change(screen.getByLabelText("Source"), { target: { value: "support-escalations" } });
    fireEvent.change(screen.getByLabelText("Description"), { target: { value: "Curated support edge cases." } });

    fireEvent.click(screen.getByRole("button", { name: "Import dataset" }));

    await waitFor(() =>
      expect(datasetHooks.mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "customer-regressions",
          description: "Curated support edge cases.",
          source: "support-escalations",
          version: "2026-04-v1"
        })
      )
    );
  });
});
