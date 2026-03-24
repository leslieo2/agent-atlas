"use client";

import { useEffect, useMemo, useState } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable
} from "@tanstack/react-table";
import { createRun, exportArtifact, listRuns, RunListFilters, RunRecord } from "@/lib/api";

const columnHelper = createColumnHelper<RunRecord>();

export default function RunDashboard() {
  const [runRecords, setRunRecords] = useState<RunRecord[]>([]);
  const [message, setMessage] = useState("Loading runs...");
  const [projectFilter, setProjectFilter] = useState("all");
  const [datasetFilter, setDatasetFilter] = useState("all");
  const [modelFilter, setModelFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [tagFilter, setTagFilter] = useState("all");
  const [createdFrom, setCreatedFrom] = useState("");
  const [createdTo, setCreatedTo] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    const filters: RunListFilters = {};
    if (projectFilter !== "all") filters.project = projectFilter;
    if (datasetFilter !== "all") filters.dataset = datasetFilter;
    if (modelFilter !== "all") filters.model = modelFilter;
    if (statusFilter !== "all") filters.status = statusFilter as RunListFilters["status"];
    if (tagFilter !== "all") filters.tag = tagFilter;
    if (createdFrom) filters.createdFrom = new Date(createdFrom).toISOString();
    if (createdTo) filters.createdTo = new Date(createdTo).toISOString();

    setMessage("Loading runs...");
    listRuns(filters)
      .then((data) => {
        setRunRecords(data);
        setMessage(data.length ? `Loaded ${data.length} runs.` : "No runs found.");
      })
      .catch((error) => setMessage(`Failed to load runs: ${error.message}`));
  }, [projectFilter, datasetFilter, modelFilter, statusFilter, tagFilter, createdFrom, createdTo]);

  const filtered = runRecords.filter((run) => {
    if (query && !run.inputSummary.toLowerCase().includes(query.toLowerCase())) return false;
    return true;
  });

  const projects = Array.from(new Set(runRecords.map((r) => r.project)));
  const datasets = Array.from(new Set(runRecords.map((r) => r.dataset)));
  const models = Array.from(new Set(runRecords.map((r) => r.model)));
  const tags = Array.from(new Set(runRecords.flatMap((r) => r.tags)));

  const columns = useMemo(
    () => [
      columnHelper.accessor("runId", { header: "Run ID", cell: (c) => c.getValue() }),
      columnHelper.accessor("inputSummary", {
        header: "Input Summary",
        cell: (c) => <span className="mono">{c.getValue()}</span>
      }),
      columnHelper.accessor("status", {
        header: "Status",
        cell: (c) => {
          const value = c.getValue() as RunRecord["status"];
          return <span className={`status-pill ${value === "failed" ? "error" : value === "running" ? "warn" : "success"}`}>{value}</span>;
        }
      }),
      columnHelper.accessor("latencyMs", {
        header: "Latency",
        cell: (c) => (c.getValue() ? `${c.getValue()} ms` : "-")
      }),
      columnHelper.accessor("tokenCost", {
        header: "Token Cost",
        cell: (c) => c.getValue().toLocaleString()
      }),
      columnHelper.accessor("toolCalls", { header: "Tool Count", cell: (c) => c.getValue() })
    ],
    []
  );

  const table = useReactTable({
    data: filtered,
    columns,
    getCoreRowModel: getCoreRowModel()
  });

  const exportLatestRun = async (format: "jsonl" | "parquet") => {
    if (!runRecords.length) return;
    const artifact = await exportArtifact({ runIds: [runRecords[0].runId], format });
    setMessage(`Exported ${artifact.artifactId} as ${format.toUpperCase()} (${artifact.sizeBytes} bytes)`);
  };

  return (
    <section>
      <div className="topbar">
        <div>
          <h2 className="section-title">Run dashboard</h2>
          <p className="kicker">Search, filter, and launch executions across projects and datasets.</p>
        </div>
        <div className="toolbar">
          <button
            className="btn"
            onClick={async () => {
              const run = await createRun({
                project: "workbench",
                dataset: "crm-v2",
                model: "gpt-4.1-mini",
                agentType: "openai-agents-sdk",
                inputSummary: "Manual run from dashboard",
                prompt: "Generate a shipping response",
                tags: ["ui"]
              });
              setRunRecords((prev) => [run, ...prev]);
              setMessage(`Created run ${run.runId}`);
            }}
          >
            New Run
          </button>
          <button className="btn" onClick={() => setMessage("Use Eval bench to run batch evaluations.")}>
            Batch Eval
          </button>
          <button
            className="btn"
            onClick={() => exportLatestRun("jsonl")}
          >
            Export JSONL
          </button>
          <button className="btn" onClick={() => exportLatestRun("parquet")}>
            Export Parquet
          </button>
        </div>
      </div>

      <div className="filters">
        <div className="field">
          <label>Project</label>
          <select value={projectFilter} onChange={(e) => setProjectFilter(e.target.value)}>
            <option value="all">all</option>
            {projects.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Dataset</label>
          <select value={datasetFilter} onChange={(e) => setDatasetFilter(e.target.value)}>
            <option value="all">all</option>
            {datasets.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Model</label>
          <select value={modelFilter} onChange={(e) => setModelFilter(e.target.value)}>
            <option value="all">all</option>
            {models.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Status</label>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="all">all</option>
            <option value="queued">queued</option>
            <option value="running">running</option>
            <option value="succeeded">succeeded</option>
            <option value="failed">failed</option>
          </select>
        </div>
        <div className="field">
          <label>Tag</label>
          <select value={tagFilter} onChange={(e) => setTagFilter(e.target.value)}>
            <option value="all">all</option>
            {tags.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Created from</label>
          <input type="datetime-local" value={createdFrom} onChange={(e) => setCreatedFrom(e.target.value)} />
        </div>
        <div className="field">
          <label>Created to</label>
          <input type="datetime-local" value={createdTo} onChange={(e) => setCreatedTo(e.target.value)} />
        </div>
        <div className="field">
          <label>Search</label>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="summary contains..." />
        </div>
      </div>

      <div className="table-shell">
        <table>
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id}>{flexRender(header.column.columnDef.header, header.getContext())}</th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="muted-note">
                  {message || "No runs match current filters."}
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <p className="muted-note" style={{ marginTop: 10 }}>{message}</p>
    </section>
  );
}
