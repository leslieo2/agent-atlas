"use client";

import { Field } from "@/src/shared/ui/Field";

export function DatasetSelector({
  datasets,
  dataset,
  onDatasetChange
}: {
  datasets: string[];
  dataset: string;
  onDatasetChange: (value: string) => void;
}) {
  return (
    <Field label="Dataset">
      <select value={dataset} onChange={(event) => onDatasetChange(event.target.value)}>
        {datasets.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
    </Field>
  );
}

