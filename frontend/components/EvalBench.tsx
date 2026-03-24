"use client";

import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { ArrowUpDown, CheckCircle2, TriangleAlert, XCircle } from "lucide-react";
import { createDataset, createEvalJob, exportArtifact, EvalResult, listDatasets, listRuns } from "@/lib/api";

export default function EvalBench() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [datasets, setDatasets] = useState<string[]>([]);
  const [runIds, setRunIds] = useState<string[]>([]);
  const [rows, setRows] = useState<EvalResult[]>([]);
  const [dataset, setDataset] = useState("crm-v2");
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState("Load datasets and run an eval.");

  const runEval = async () => {
    if (!dataset || !runIds[0]) return;
    const job = await createEvalJob({
      runIds: [runIds[0]],
      dataset,
      evaluators: ["rule", "judge", "tool-correctness"]
    });
    setRows(job.results);
    setMessage(`Eval job ${job.jobId} finished with status ${job.status}`);
  };

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const text = await file.text();
    const rows = text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line, index) => {
        const parsed = JSON.parse(line) as { sample_id?: string; input: string; expected?: string; tags?: string[] };
        return {
          sampleId: parsed.sample_id ?? `sample-${index + 1}`,
          input: parsed.input,
          expected: parsed.expected ?? null,
          tags: parsed.tags ?? []
        };
      });

    const datasetName = file.name.replace(/\.jsonl$/i, "") || `dataset-${Date.now()}`;
    const dataset = await createDataset({ name: datasetName, rows });
    setDatasets((prev) => Array.from(new Set([...prev, dataset.name])));
    setDataset(dataset.name);
    setMessage(`Uploaded dataset ${dataset.name} with ${dataset.rows.length} rows.`);
    event.target.value = "";
  };

  useEffect(() => {
    listDatasets().then((data) => {
      const names = data.map((item) => item.name);
      setDatasets(names);
      if (names[0]) setDataset(names[0]);
    });
    listRuns().then((data) => setRunIds(data.map((item) => item.runId)));
  }, []);

  const totals = useMemo(() => {
    if (!rows.length) {
      return { successRate: 0, toolSuccessRate: 0, latencyMs: 0, tokenUsage: 0, judgeScore: 0 };
    }
    const denom = rows.length;
    const passCount = rows.filter((row) => row.status === "pass").length;
    const avgScore = rows.reduce((acc, row) => acc + row.score, 0) / denom;
    return {
      successRate: Math.round((passCount / denom) * 100),
      toolSuccessRate: Math.round((passCount / denom) * 100),
      latencyMs: 0,
      tokenUsage: 0,
      judgeScore: Number(avgScore.toFixed(2))
    };
  }, [rows]);

  const failed = rows.filter((r) => r.status === "fail").length;

  return (
    <section>
      <div className="topbar">
        <div>
          <h2 className="section-title">Eval bench</h2>
          <p className="kicker">Benchmark runs against datasets and inspect sample-level failures quickly.</p>
        </div>
        <div className="toolbar">
          <input
            ref={fileInputRef}
            type="file"
            accept=".jsonl"
            style={{ display: "none" }}
            onChange={handleUpload}
          />
          <button className="btn" onClick={() => fileInputRef.current?.click()}>
            Upload JSONL
          </button>
          <button className="btn" onClick={runEval}>
            Run batch eval
          </button>
          <button
            className="btn"
            onClick={async () => {
              if (!runIds[0]) return;
              const artifact = await exportArtifact({ runIds: [runIds[0]], format: "jsonl" });
              setMessage(`Exported artifacts to ${artifact.path}`);
            }}
          >
            Export artifacts
          </button>
        </div>
      </div>

      <div className="metrics">
        <div className="metric">
          <div className="metric-label">Success rate</div>
          <div className="metric-value">{totals.successRate}%</div>
        </div>
        <div className="metric">
          <div className="metric-label">Tool success</div>
          <div className="metric-value">{totals.toolSuccessRate}%</div>
        </div>
        <div className="metric">
          <div className="metric-label">Latency</div>
          <div className="metric-value">{totals.latencyMs}ms</div>
        </div>
        <div className="metric">
          <div className="metric-label">Token usage</div>
          <div className="metric-value">{totals.tokenUsage}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Judge score</div>
          <div className="metric-value">{totals.judgeScore.toFixed(1)}</div>
        </div>
      </div>

      <div className="divider" />

      <div className="filters">
        <div className="field">
          <label>Dataset</label>
          <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
            {datasets.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Search sample</label>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="sample id / run id" />
        </div>
        <div className="field" style={{ alignSelf: "end" }}>
          <button className="btn" onClick={runEval}>
            <ArrowUpDown size={14} /> Refresh metrics
          </button>
        </div>
      </div>

      <div className="run-grid">
        <div className="table-shell">
          <h3 className="panel-title">Run comparison table</h3>
          <table>
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Sample ID</th>
                <th>Success</th>
                <th>Score</th>
                <th>Reason</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows
                .filter((row) => row.runId.includes(query) || row.sampleId.includes(query))
                .map((row) => (
                  <tr key={row.sampleId}>
                    <td>{row.runId.slice(0, 8)}</td>
                    <td>{row.sampleId}</td>
                    <td>{row.status === "pass" ? "pass" : "fail"}</td>
                    <td>{row.score}</td>
                    <td>{row.reason ?? "-"}</td>
                    <td>{row.status}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        <div className="table-shell">
          <h3 className="panel-title">Failing samples ({failed})</h3>
          {rows
            .filter((r) => r.status === "fail" || r.status === "pass")
            .map((sample) => (
              <div key={sample.sampleId} className="step-item" style={{ marginBottom: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <strong>{sample.sampleId}</strong>
                  {sample.status === "pass" ? <CheckCircle2 size={16} color="#6effa6" /> : <XCircle size={16} color="#ff7a87" />}
                </div>
                <p className="muted-note">{sample.input}</p>
                <p className="muted-note">
                  Run {sample.runId.slice(0, 8)} · score {sample.score}
                </p>
                <p className="muted-note">
                  {sample.status === "fail" ? <TriangleAlert size={12} /> : null} {sample.reason ?? "no issues"}
                </p>
              </div>
            ))}
          <p className="muted-note" style={{ marginTop: 8 }}>{message}</p>
        </div>
      </div>
    </section>
  );
}
