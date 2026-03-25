import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import RunDashboardWidget from "@/src/widgets/run-dashboard/RunDashboardWidget";
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
    model: "gpt-4.1-mini",
    agentType: "langchain",
    tags: ["langchain"],
    createdAt: "2026-03-23T10:03:00Z"
  }
];

vi.mock("@/src/entities/run/api", () => ({
  listRuns: vi.fn(),
  createRun: vi.fn()
}));

vi.mock("@/src/entities/artifact/api", () => ({
  exportArtifact: vi.fn()
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

describe("RunDashboard integration", () => {
  beforeEach(() => {
    (runApi.listRuns as unknown as MockedApiFn).mockReset();
    (runApi.createRun as unknown as MockedApiFn).mockReset();
    (artifactApi.exportArtifact as unknown as MockedApiFn).mockReset();
    (runApi.listRuns as unknown as MockedApiFn).mockResolvedValue(mockedRuns);
    (runApi.createRun as unknown as MockedApiFn).mockResolvedValue({
      ...mockedRuns[0],
      runId: "run-003",
      inputSummary: "Manual run from dashboard",
      status: "queued"
    });
    (artifactApi.exportArtifact as unknown as MockedApiFn)
      .mockResolvedValueOnce({
        artifactId: "artifact-001",
        path: "/tmp/artifact.jsonl",
        sizeBytes: 11
      })
      .mockResolvedValueOnce({
        artifactId: "artifact-002",
        path: "/tmp/artifact.parquet",
        sizeBytes: 21
      });
  });

  it("loads runs and can create a new run", async () => {
    render(<RunDashboardWidget />);

    expect(await screen.findByText("Loaded 2 runs.")).toBeInTheDocument();
    expect(screen.getByText("Generate a booking itinerary from CRM contact data")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "New Run" }));
    expect(await screen.findByText("Created run run-003")).toBeInTheDocument();
  });

  it("exports jsonl and parquet artifacts for the latest run", async () => {
    render(<RunDashboardWidget />);

    expect(await screen.findByText("Loaded 2 runs.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Export JSONL" }));
    expect(artifactApi.exportArtifact).toHaveBeenNthCalledWith(1, {
      runIds: ["run-001"],
      format: "jsonl"
    });
    expect(await screen.findByText("Exported artifact-001 as JSONL (11 bytes)")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Export Parquet" }));
    expect(artifactApi.exportArtifact).toHaveBeenNthCalledWith(2, {
      runIds: ["run-001"],
      format: "parquet"
    });
    expect(await screen.findByText("Exported artifact-002 as PARQUET (21 bytes)")).toBeInTheDocument();
  });
});
