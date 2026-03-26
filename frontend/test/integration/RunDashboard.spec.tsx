import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as datasetApi from "@/src/entities/dataset/api";
import RunDashboardWidget from "@/src/widgets/run-dashboard/RunDashboardWidget";
import { renderWithQueryClient } from "@/test/setup";
import * as artifactApi from "@/src/entities/artifact/api";
import * as runApi from "@/src/entities/run/api";

vi.mock("@tanstack/react-table", () => {
  const createColumnHelper = () => ({
    accessor: (key: string, options: { header: string; cell: (context: { getValue: () => unknown }) => unknown }) => ({
      id: key,
      accessorKey: key,
      columnDef: {
        header: options.header,
        cell: options.cell
      }
    })
  });

  return {
    createColumnHelper,
    flexRender: (renderer: unknown, context: unknown) =>
      typeof renderer === "function" ? renderer(context) : renderer,
    getCoreRowModel: () => () => ({ rows: [] }),
    useReactTable: ({ data, columns }: { data: Array<Record<string, unknown>>; columns: Array<{ id?: string; accessorKey?: string; columnDef: { header: string; cell: (context: { getValue: () => unknown }) => unknown } }> }) => ({
      getHeaderGroups: () => [
        {
          id: "header-group",
          headers: columns.map((column, index) => ({
            id: column.id ?? column.accessorKey ?? `header-${index}`,
            column: {
              columnDef: {
                header: column.columnDef.header
              }
            },
            getContext: () => ({})
          }))
        }
      ],
      getRowModel: () => ({
        rows: data.map((row, rowIndex) => ({
          id: `row-${rowIndex}`,
          getVisibleCells: () =>
            columns.map((column, columnIndex) => ({
              id: `${rowIndex}-${column.id ?? column.accessorKey ?? columnIndex}`,
              column: {
                columnDef: {
                  cell: column.columnDef.cell
                }
              },
              getContext: () => ({
                getValue: () => row[column.accessorKey ?? ""]
              })
            }))
        }))
      })
    })
  };
});

const mockedRuns = [
  {
    runId: "run-001",
    inputSummary: "Generate a booking itinerary from CRM contact data",
    status: "succeeded" as const,
    latencyMs: 1410,
    tokenCost: 1280,
    toolCalls: 5,
    project: "sales-assistant",
    dataset: "crm-v2",
    agentId: "customer_service",
    model: "gpt-4.1-mini",
    agentType: "openai-agents-sdk",
    tags: ["agent-sdk", "mcp"],
    createdAt: "2026-03-23T09:12:00Z"
  },
  {
    runId: "run-002",
    inputSummary: "Summarize support tickets",
    status: "failed" as const,
    latencyMs: 960,
    tokenCost: 910,
    toolCalls: 3,
    project: "support-router",
    dataset: "support-incidents",
    agentId: "",
    model: "gpt-4.1-mini",
    agentType: "langchain",
    tags: ["langchain"],
    createdAt: "2026-03-23T10:03:00Z"
  }
];

vi.mock("@/src/entities/run/api", () => ({
  listRuns: vi.fn()
}));

vi.mock("@/src/entities/dataset/api", () => ({
  listDatasets: vi.fn()
}));

vi.mock("@/src/entities/artifact/api", () => ({
  listArtifacts: vi.fn(),
  exportArtifact: vi.fn(),
  getArtifactDownloadUrl: vi.fn(() => "http://127.0.0.1:8000/api/v1/artifacts/artifact-history-001")
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

describe("RunDashboard integration", () => {
  beforeEach(() => {
    (datasetApi.listDatasets as unknown as MockedApiFn).mockReset();
    (runApi.listRuns as unknown as MockedApiFn).mockReset();
    (artifactApi.listArtifacts as unknown as MockedApiFn).mockReset();
    (artifactApi.exportArtifact as unknown as MockedApiFn).mockReset();
    (datasetApi.listDatasets as unknown as MockedApiFn).mockResolvedValue([{ name: "customer-live", rows: [] }]);
    (runApi.listRuns as unknown as MockedApiFn).mockResolvedValue(mockedRuns);
    (artifactApi.listArtifacts as unknown as MockedApiFn).mockResolvedValue([
      {
        artifactId: "artifact-history-001",
        format: "jsonl",
        runIds: ["run-001", "run-002"],
        createdAt: "2026-03-23T11:02:00Z",
        path: "/tmp/artifact-history-001.jsonl",
        sizeBytes: 52
      },
      {
        artifactId: "artifact-history-002",
        format: "parquet",
        runIds: ["run-001"],
        createdAt: "2026-03-23T10:55:00Z",
        path: "/tmp/artifact-history-002.parquet",
        sizeBytes: 86
      }
    ]);
    (artifactApi.exportArtifact as unknown as MockedApiFn)
      .mockResolvedValueOnce({
        artifactId: "artifact-001",
        format: "jsonl",
        runIds: ["run-001"],
        createdAt: "2026-03-23T11:01:00Z",
        path: "/tmp/artifact.jsonl",
        sizeBytes: 11
      })
      .mockResolvedValueOnce({
        artifactId: "artifact-002",
        format: "parquet",
        runIds: ["run-001"],
        createdAt: "2026-03-23T11:02:00Z",
        path: "/tmp/artifact.parquet",
        sizeBytes: 21
      });
  });

  it("loads runs and links new runs to Playground", async () => {
    renderWithQueryClient(<RunDashboardWidget />);

    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(artifactApi.listArtifacts).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("Loaded 2 runs.")).toBeInTheDocument();
    expect(screen.getByText("Generate a booking itinerary from CRM contact data")).toBeVisible();

    expect(screen.getByRole("link", { name: "New Run" })).toHaveAttribute("href", "/playground?dataset=customer-live");
  });

  it("exports jsonl and parquet artifacts for the filtered runs", async () => {
    renderWithQueryClient(<RunDashboardWidget />);

    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(artifactApi.listArtifacts).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("Loaded 2 runs.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Export 2 runs as JSONL" }));
    await waitFor(() => {
      expect(artifactApi.exportArtifact).toHaveBeenNthCalledWith(1, {
        runIds: ["run-001", "run-002"],
        format: "jsonl"
      });
    });
    expect(await screen.findByText("Exported 2 runs as JSONL.")).toBeInTheDocument();
    expect(screen.getByText("11 bytes · current filter result")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download JSONL" })).toHaveAttribute(
      "href",
      "http://127.0.0.1:8000/api/v1/artifacts/artifact-history-001"
    );

    fireEvent.click(screen.getByRole("button", { name: "Export 2 runs as Parquet" }));
    await waitFor(() => {
      expect(artifactApi.exportArtifact).toHaveBeenNthCalledWith(2, {
        runIds: ["run-001", "run-002"],
        format: "parquet"
      });
    });
    expect(await screen.findByText("Exported 2 runs as Parquet.")).toBeInTheDocument();
    expect(screen.getByText("21 bytes · current filter result")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download Parquet" })).toHaveAttribute(
      "href",
      "http://127.0.0.1:8000/api/v1/artifacts/artifact-history-001"
    );
  });

  it("renders artifact history from the export listing endpoint", async () => {
    renderWithQueryClient(<RunDashboardWidget />);

    await waitFor(() => expect(artifactApi.listArtifacts).toHaveBeenCalledTimes(1));

    expect(await screen.findByText("Artifact history")).toBeInTheDocument();
    expect(screen.getByText("artifact-history-001")).toBeInTheDocument();
    expect(screen.getByText("2 runs")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download JSONL artifact" })).toHaveAttribute(
      "href",
      "http://127.0.0.1:8000/api/v1/artifacts/artifact-history-001"
    );
  });

  it("links ad-hoc creation to Playground when no dataset exists", async () => {
    (datasetApi.listDatasets as unknown as MockedApiFn).mockResolvedValue([]);

    renderWithQueryClient(<RunDashboardWidget />);

    await waitFor(() => expect(datasetApi.listDatasets).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("link", { name: "New Run" })).toHaveAttribute("href", "/playground");
  });
});
