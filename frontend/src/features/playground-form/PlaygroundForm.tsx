"use client";

import type { AgentRecord } from "@/src/entities/agent/model";
import type { Dataset } from "@/src/entities/dataset/model";
import { Field } from "@/src/shared/ui/Field";

type Props = {
  prompt: string;
  agentId: string;
  agents: AgentRecord[];
  dataset: string;
  datasets: Dataset[];
  tagsText: string;
  onPromptChange: (value: string) => void;
  onAgentIdChange: (value: string) => void;
  onDatasetChange: (value: string) => void;
  onTagsTextChange: (value: string) => void;
};

export function PlaygroundForm({
  prompt,
  agentId,
  agents,
  dataset,
  datasets,
  tagsText,
  onPromptChange,
  onAgentIdChange,
  onDatasetChange,
  onTagsTextChange
}: Props) {
  return (
    <>
      <Field label="Prompt" htmlFor="playground-prompt">
        <textarea
          id="playground-prompt"
          rows={7}
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
        />
      </Field>
      <div className="two-col" style={{ marginTop: 12 }}>
        <Field label="Agent" htmlFor="playground-agent">
          <select id="playground-agent" value={agentId} onChange={(event) => onAgentIdChange(event.target.value)}>
            {agents.map((agent) => (
              <option key={agent.agentId} value={agent.agentId}>
                {agent.name} ({agent.agentId})
              </option>
            ))}
          </select>
        </Field>
        <Field label="Dataset" htmlFor="playground-dataset">
          <select id="playground-dataset" value={dataset} onChange={(event) => onDatasetChange(event.target.value)}>
            <option value="">No dataset attached</option>
            {datasets.map((item) => (
              <option key={item.name} value={item.name}>
                {item.name}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Field label="Execution tags" htmlFor="playground-tags" wide>
        <input
          id="playground-tags"
          value={tagsText}
          onChange={(event) => onTagsTextChange(event.target.value)}
          placeholder="retry, support, staging"
        />
      </Field>
    </>
  );
}
