"use client";

import { useEffect, useState } from "react";
import { createRun, getTrajectory, listRuns } from "@/lib/api";

export default function Playground() {
  const [prompt, setPrompt] = useState("Draft a concise customer response for delayed shipping.");
  const [agentType, setAgentType] = useState("OpenAI Agents SDK");
  const [model, setModel] = useState("gpt-4.1-mini");
  const [tools, setTools] = useState("crm_lookup, pricing_service, policy_guard");
  const [latestRunId, setLatestRunId] = useState("");
  const [log, setLog] = useState("trace: waiting for manual run...\n");

  useEffect(() => {
    listRuns().then((runs) => {
      if (runs[0]) setLatestRunId(runs[0].runId);
    });
  }, []);

  const runManual = async () => {
    const run = await createRun({
      project: "playground",
      dataset: "crm-v2",
      model,
      agentType: agentType === "LangChain" ? "langchain" : "openai-agents-sdk",
      inputSummary: prompt.slice(0, 80),
      prompt,
      tags: tools.split(",").map((item) => item.trim()).filter(Boolean)
    });
    setLatestRunId(run.runId);
    setLog(
      [
        `run_id: ${run.runId}`,
        `agent: ${agentType}`,
        `model: ${model}`,
        `prompt: ${prompt}`,
        `tools: ${tools}`,
        `status: ${run.status}`,
        `token_cost: ${run.tokenCost}`,
        `latency_ms: ${run.latencyMs}`
      ].join("\n")
    );
  };

  return (
    <section>
      <div className="topbar">
        <div>
          <h2 className="section-title">Playground</h2>
          <p className="kicker">Manual single-run entrypoint for smoke checks and quick trace generation.</p>
        </div>
        <div className="toolbar">
          <button className="btn" onClick={() => setPrompt("Can you create a shipping itinerary?")}>
            Attach dataset sample
          </button>
          <button
            className="btn"
            onClick={async () => {
              if (!latestRunId) return;
              const steps = await getTrajectory(latestRunId);
              setLog(
                steps.length
                  ? steps.map((step) => `${step.id} | ${step.stepType} | ${step.output}`).join("\n")
                  : `No trajectory found for ${latestRunId}`
              );
            }}
          >
            Open latest trace
          </button>
        </div>
      </div>

      <div className="layout-two">
        <div className="chart-shell">
          <h3 className="panel-title">Prompt and runtime settings</h3>
          <div className="field" style={{ marginBottom: 12 }}>
            <label>Prompt</label>
            <textarea rows={7} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          </div>
          <div className="two-col">
            <div className="field">
              <label>Agent type</label>
              <select value={agentType} onChange={(e) => setAgentType(e.target.value)}>
                <option>OpenAI Agents SDK</option>
                <option>LangChain</option>
              </select>
            </div>
            <div className="field">
              <label>Model</label>
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                <option>gpt-4.1-mini</option>
                <option>gpt-4.1</option>
                <option>gpt-5-mini</option>
              </select>
            </div>
          </div>
          <div className="field" style={{ marginTop: 12 }}>
            <label>Tool selection (comma-separated)</label>
            <input value={tools} onChange={(e) => setTools(e.target.value)} />
          </div>
          <div className="toolbar" style={{ marginTop: 12 }}>
            <button className="btn" onClick={runManual}>
              Run now
            </button>
            <button className="btn" onClick={() => navigator.clipboard?.writeText(log)}>
              Save snapshot
            </button>
          </div>
        </div>

        <div className="chart-shell">
          <h3 className="panel-title">Execution output</h3>
          <pre className="output-log mono">{log}</pre>
        </div>
      </div>
    </section>
  );
}
