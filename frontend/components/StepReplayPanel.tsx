"use client";

import { useEffect, useMemo, useState } from "react";
import { DiffEditor } from "@monaco-editor/react";
import { createReplay, createRun, getTrajectory, listRuns, RunRecord, TrajectoryStep } from "@/lib/api";

export default function StepReplayPanel() {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [selectedRun, setSelectedRun] = useState("");
  const [steps, setSteps] = useState<TrajectoryStep[]>([]);
  const [selectedStepId, setSelectedStepId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [toolPayload, setToolPayload] = useState('{\n  "carrier": "FedEx"\n}');
  const [model, setModel] = useState("gpt-4.1-mini");
  const [isReplaying, setIsReplaying] = useState(false);
  const [lastDiff, setLastDiff] = useState("Waiting for replay...");

  const candidate = steps.find((step) => step.id === selectedStepId) ?? null;

  useEffect(() => {
    listRuns().then((data) => {
      setRuns(data);
      if (data[0]) setSelectedRun(data[0].runId);
    });
  }, []);

  useEffect(() => {
    if (!selectedRun) return;
    getTrajectory(selectedRun).then((data) => {
      setSteps(data);
      if (data[0]) {
        setSelectedStepId(data[0].id);
        setPrompt(data[0].prompt);
        setModel(data[0].model);
      }
    });
  }, [selectedRun]);

  useEffect(() => {
    if (!candidate) return;
    setPrompt(candidate.prompt);
    setModel(candidate.model);
  }, [selectedStepId]);

  const modifiedOutput = useMemo(() => {
    if (!candidate) return "Select a step to replay.";
    return `Patched output:
${candidate.output} -> with model ${model} and payload ${toolPayload.slice(0, 32)}...`;
  }, [candidate, model, toolPayload]);

  return (
    <section>
      <div className="topbar">
        <div>
          <h2 className="section-title">Step replay</h2>
          <p className="kicker">Replay a single trajectory step and compare the diff before creating a new candidate run.</p>
        </div>
        <button
          type="button"
          className="btn"
          disabled={isReplaying || !candidate}
          onClick={async () => {
            if (!candidate) return;
            setIsReplaying(true);
            try {
              const result = await createReplay({
                runId: candidate.runId,
                stepId: candidate.id,
                editedPrompt: prompt,
                model,
                toolOverrides: JSON.parse(toolPayload),
                rationale: "Replay from UI"
              });
              setLastDiff(result.diff || `Replay completed: ${result.replayId}`);
            } catch (error) {
              setLastDiff(error instanceof Error ? error.message : "Replay failed");
            } finally {
              setIsReplaying(false);
            }
          }}
        >
          Replay step
        </button>
      </div>

      <div className="run-grid">
        <div className="chart-shell">
          <h3 className="panel-title">Replay controls</h3>
          <div className="two-col">
            <div className="field">
              <label>Run</label>
              <select value={selectedRun} onChange={(e) => setSelectedRun(e.target.value)}>
                {runs.map((run) => (
                  <option key={run.runId} value={run.runId}>
                    {run.runId.slice(0, 8)} · {run.project}
                  </option>
                ))}
              </select>
              <label>Step</label>
              <select value={selectedStepId} onChange={(e) => setSelectedStepId(e.target.value)}>
                {steps.map((step) => (
                  <option key={step.id} value={step.id}>
                    {step.id} · {step.stepType}
                  </option>
                ))}
              </select>
              <label>Editable prompt</label>
              <textarea rows={6} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
            </div>
            <div className="field">
              <label>Model switcher</label>
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                <option>gpt-4.1</option>
                <option>gpt-4.1-mini</option>
                <option>gpt-5-mini</option>
              </select>
              <label>Tool parameter editor</label>
              <textarea rows={5} value={toolPayload} onChange={(e) => setToolPayload(e.target.value)} />
            </div>
          </div>
          <p className="muted-note" style={{ marginTop: 10 }}>
            Step: {candidate?.id ?? "-"} · Source run: {candidate?.runId ?? "-"} · Tool output baseline:
          </p>
          <p className="output-log mono">{candidate?.output ?? "No baseline output."}</p>
          <p className="muted-note">
            {isReplaying ? "Replay running..." : "Replay idle. The output diff updates after replay."}
          </p>
        </div>

        <div className="chart-shell">
          <h3 className="panel-title">Prompt and output diff</h3>
          <DiffEditor
            original={`Original:
${candidate?.prompt ?? ""}\n\nOutput:
${candidate?.output ?? ""}`}
            modified={`Replayed prompt:
${prompt}\n\n${modifiedOutput}`}
            language="json"
            height="300px"
            options={{
              renderSideBySide: true,
              readOnly: false,
              minimap: { enabled: false },
              fontSize: 12
            }}
          />
          <p className="muted-note" style={{ marginTop: 8 }}>
            Replay diff: {lastDiff}
          </p>
          <div className="toolbar" style={{ marginTop: 8 }}>
            <button
              className="btn"
              onClick={() => navigator.clipboard?.writeText(lastDiff)}
            >
              Save as candidate
            </button>
            <button
              className="btn"
              onClick={async () => {
                if (!candidate) return;
                const run = await createRun({
                  project: "replay-candidate",
                  dataset: "crm-v2",
                  model,
                  agentType: "openai-agents-sdk",
                  inputSummary: `Replay candidate from ${candidate.id}`,
                  prompt,
                  tags: ["replay"]
                });
                setLastDiff(`Promoted replay to new run ${run.runId}`);
              }}
            >
              Promote to new run
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
