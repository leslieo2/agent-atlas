"use client";

import { Field } from "@/src/shared/ui/Field";

type Props = {
  prompt: string;
  agentType: string;
  model: string;
  dataset: string;
  datasets: string[];
  tools: string;
  onPromptChange: (value: string) => void;
  onAgentTypeChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onDatasetChange: (value: string) => void;
  onToolsChange: (value: string) => void;
};

export function PlaygroundForm({
  prompt,
  agentType,
  model,
  dataset,
  datasets,
  tools,
  onPromptChange,
  onAgentTypeChange,
  onModelChange,
  onDatasetChange,
  onToolsChange
}: Props) {
  return (
    <>
      <Field label="Prompt">
        <textarea rows={7} value={prompt} onChange={(event) => onPromptChange(event.target.value)} />
      </Field>
      <div className="two-col" style={{ marginTop: 12 }}>
        <Field label="Agent type">
          <select value={agentType} onChange={(event) => onAgentTypeChange(event.target.value)}>
            <option>OpenAI Agents SDK</option>
            <option>LangChain</option>
          </select>
        </Field>
        <Field label="Model">
          <select value={model} onChange={(event) => onModelChange(event.target.value)}>
            <option>gpt-4.1-mini</option>
            <option>gpt-4.1</option>
            <option>gpt-5-mini</option>
          </select>
        </Field>
        <Field label="Dataset">
          <select value={dataset} onChange={(event) => onDatasetChange(event.target.value)} disabled={!datasets.length}>
            {!datasets.length ? (
              <option value="">No datasets available</option>
            ) : !datasets.includes(dataset) ? (
              <option value="">Select a dataset</option>
            ) : null}
            {datasets.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Field label="Tool selection (comma-separated)">
        <input value={tools} onChange={(event) => onToolsChange(event.target.value)} />
      </Field>
    </>
  );
}
