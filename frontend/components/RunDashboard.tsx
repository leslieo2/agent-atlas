"use client";

import { useEffect, useMemo, useState } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable
} from "@tanstack/react-table";
import { createRun, exportArtifact, listRuns, RunRecord } from "@/lib/api";

const columnHelper = createColumnHelper<RunRecord>();

export default function RunDashboard() {
  const [runRecords, setRunRecords] = useState<RunRecord[]>([]);
  const [message, setMessage] = useState("Loading runs...");
  const [projectFilter, setProjectFilter] = useState("all");
  const [datasetFilter, setDatasetFilter] = useState("all");
  const [modelFilter, setModelFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    listRuns()
      .then((data) => {
        setRunRecords(data);
        setMessage(data.length ? `Loaded ${data.length} runs.` : "No runs found.");
      })
      .catch((error) => setMessage(`Failed to load runs: ${error.message}`));
  }, []);

  const filtered = runRecords.filter((run) => {
    if (projectFilter !== "all" && run.project !== projectFilter) return false;
    if (datasetFilter !== "all" && run.dataset !== datasetFilter) return false;
    if (modelFilter !== "all" && run.model !== modelFilter) return false;
    if (statusFilter !== "all" && run.status !== statusFilter) return false;
    if (query && !run.inputSummary.toLowerCase().includes(query.toLowerCase())) return false;
    return true;
  });

  const projects = Array.from(new Set(runRecords.map((r) => r.project)));
  const datasets = Array.from(new Set(runRecords.map((r) => r.dataset)));
  const models = Array.from(new Set(runRecords.map((r) => r.model)));

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
            onClick={async () => {
              if (!runRecords.length) return;
              const artifact = await exportArtifact({ runIds: [runRecords[0].runId], format: "jsonl" });
              setMessage(`Exported ${artifact.artifactId} (${artifact.sizeBytes} bytes)`);
            }}
          >
            Export JSONL
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
