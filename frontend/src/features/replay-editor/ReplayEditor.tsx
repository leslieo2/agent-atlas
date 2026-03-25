"use client";

import { Field } from "@/src/shared/ui/Field";

type Props = {
  prompt: string;
  model: string;
  toolPayload: string;
  onPromptChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onToolPayloadChange: (value: string) => void;
};

export function ReplayEditor({
  prompt,
  model,
  toolPayload,
  onPromptChange,
  onModelChange,
  onToolPayloadChange
}: Props) {
  return (
    <div className="two-col">
      <Field label="Editable prompt" htmlFor="step-replay-prompt">
        <textarea
          id="step-replay-prompt"
          rows={7}
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
        />
      </Field>
      <div className="field">
        <Field label="Model switcher" htmlFor="step-replay-model">
          <select id="step-replay-model" value={model} onChange={(event) => onModelChange(event.target.value)}>
            <option>gpt-4.1</option>
            <option>gpt-4.1-mini</option>
            <option>gpt-5-mini</option>
          </select>
        </Field>
        <Field label="Tool parameter editor" htmlFor="step-replay-tool-params">
          <textarea
            id="step-replay-tool-params"
            rows={7}
            value={toolPayload}
            onChange={(event) => onToolPayloadChange(event.target.value)}
          />
        </Field>
      </div>
    </div>
  );
}

