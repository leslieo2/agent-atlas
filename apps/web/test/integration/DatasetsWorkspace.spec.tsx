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
        description: "Support escalation data",
        source: "customer-support-regression",
        currentVersionId: "dataset-version-crm-v2",
        version: "2026-03-rl-v2",
        createdAt: "2026-03-24T00:00:00Z",
        rows: [
          {
            sampleId: "sample-1",
            input: "where is my order?",
            expected: "status lookup",
            tags: ["shipping"],
            slice: "shipping",
            source: "crm",
            metadata: null,
            exportEligible: true
          },
          {
            sampleId: "sample-2",
            input: "cancel my order",
            expected: null,
            tags: ["returns"],
            slice: "returns",
            source: "crm",
            metadata: null,
            exportEligible: false
          }
        ],
        versions: [
          {
            datasetVersionId: "dataset-version-crm-v2",
            datasetName: "crm-v2",
            version: "2026-03-rl-v2",
            createdAt: "2026-03-24T00:00:00Z",
            rowCount: 2,
            rows: [
              {
                sampleId: "sample-1",
                input: "where is my order?",
                expected: "status lookup",
                tags: ["shipping"],
                slice: "shipping",
                source: "crm",
                metadata: null,
                exportEligible: true
              },
              {
                sampleId: "sample-2",
                input: "cancel my order",
                expected: null,
                tags: ["returns"],
                slice: "returns",
                source: "crm",
                metadata: null,
                exportEligible: false
              }
            ]
          }
        ]
      }
    ]);
    (datasetApi.createDataset as unknown as MockedApiFn).mockResolvedValue({
      name: "returns-review",
      description: "High-value failures",
      source: "support_ticket_backfill",
      currentVersionId: "dataset-version-returns-review",
      version: "2026-03-rl-v1",
      createdAt: "2026-03-25T00:00:00Z",
      rows: [
        {
          sampleId: "returns-review-sample-1",
          input: "review order return",
          expected: null,
          tags: ["returns"],
          slice: "hard-cases",
          source: "support_ticket_backfill",
          metadata: null,
          exportEligible: true
        }
      ],
      versions: [
        {
          datasetVersionId: "dataset-version-returns-review",
          datasetName: "returns-review",
          version: "2026-03-rl-v1",
          createdAt: "2026-03-25T00:00:00Z",
          rowCount: 1,
          rows: [
            {
              sampleId: "returns-review-sample-1",
              input: "review order return",
              expected: null,
              tags: ["returns"],
              slice: "hard-cases",
              source: "support_ticket_backfill",
              metadata: null,
              exportEligible: true
            }
          ]
        }
      ]
    });
  });

  it("loads dataset assets, filters rows, and imports a new dataset with metadata", async () => {
    renderWithQueryClient(<DatasetsWorkspace />);

    expect(await screen.findByRole("heading", { name: "Datasets" })).toBeInTheDocument();
    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalled());
    expect(await screen.findByText("where is my order?")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open in experiments" })).toHaveAttribute(
      "href",
      "/experiments?datasetVersion=dataset-version-crm-v2"
    );
    expect(screen.getByText("Version 2026-03-rl-v2")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Slice filter"), { target: { value: "returns" } });
    expect(screen.getByText("cancel my order")).toBeInTheDocument();
    expect(screen.queryByText("where is my order?")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Dataset name"), { target: { value: "returns-review" } });
    fireEvent.change(screen.getByLabelText("Version"), { target: { value: "2026-03-rl-v1" } });
    fireEvent.change(screen.getByLabelText("Source"), { target: { value: "support_ticket_backfill" } });
    fireEvent.change(screen.getByLabelText("Description"), { target: { value: "High-value failures" } });

    const upload = screen.getByLabelText("Upload dataset JSONL");
    const file = new File(
      [
        JSON.stringify({
          sample_id: "returns-review-sample-1",
          input: "review order return",
          expected: null,
          tags: ["returns"],
          slice: "hard-cases",
          source: "support_ticket_backfill",
          export_eligible: true
        })
      ],
      "returns-review.jsonl",
      { type: "application/jsonl" }
    );
    fireEvent.change(upload, { target: { files: [file] } });

    expect(await screen.findByText(/Ready to import 1 sample from returns-review\.jsonl\./)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Import dataset" }));

    await waitFor(() =>
      expect(datasetApi.createDataset).toHaveBeenCalledWith({
        name: "returns-review",
        description: "High-value failures",
        source: "support_ticket_backfill",
        version: "2026-03-rl-v1",
        rows: [
          {
            sampleId: "returns-review-sample-1",
            input: "review order return",
            expected: null,
            tags: ["returns"],
            slice: "hard-cases",
            source: "support_ticket_backfill",
            metadata: null,
            exportEligible: true
          }
        ]
      })
    );

    expect(await screen.findByText(/Imported dataset returns-review with 1 sample\./)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open imported dataset in experiments" })).toHaveAttribute(
      "href",
      "/experiments?datasetVersion=dataset-version-returns-review"
    );
    expect(screen.queryByRole("button", { name: "Create dataset" })).not.toBeInTheDocument();
  });
});
