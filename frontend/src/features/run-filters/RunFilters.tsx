"use client";

import { Field } from "@/src/shared/ui/Field";
import type { RunListFilters } from "@/src/entities/run/model";

export type RunFilterState = {
  projectFilter: string;
  datasetFilter: string;
  modelFilter: string;
  statusFilter: string;
  tagFilter: string;
  createdFrom: string;
  createdTo: string;
  query: string;
};

type Props = {
  options: {
    projects: string[];
    datasets: string[];
    models: string[];
    tags: string[];
  };
  state: RunFilterState;
  onChange: (next: RunFilterState) => void;
};

export function buildRunFilters(state: RunFilterState): RunListFilters {
  const filters: RunListFilters = {};

  if (state.projectFilter !== "all") filters.project = state.projectFilter;
  if (state.datasetFilter !== "all") filters.dataset = state.datasetFilter;
  if (state.modelFilter !== "all") filters.model = state.modelFilter;
  if (state.statusFilter !== "all") filters.status = state.statusFilter as RunListFilters["status"];
  if (state.tagFilter !== "all") filters.tag = state.tagFilter;
  if (state.createdFrom) filters.createdFrom = new Date(state.createdFrom).toISOString();
  if (state.createdTo) filters.createdTo = new Date(state.createdTo).toISOString();

  return filters;
}

export function RunFilters({ options, state, onChange }: Props) {
  return (
    <div className="filters filters-dense">
      <Field label="Project">
        <select
          value={state.projectFilter}
          onChange={(event) => onChange({ ...state, projectFilter: event.target.value })}
        >
          <option value="all">all</option>
          {options.projects.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Dataset">
        <select
          value={state.datasetFilter}
          onChange={(event) => onChange({ ...state, datasetFilter: event.target.value })}
        >
          <option value="all">all</option>
          {options.datasets.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Model">
        <select value={state.modelFilter} onChange={(event) => onChange({ ...state, modelFilter: event.target.value })}>
          <option value="all">all</option>
          {options.models.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Status">
        <select
          value={state.statusFilter}
          onChange={(event) => onChange({ ...state, statusFilter: event.target.value })}
        >
          <option value="all">all</option>
          <option value="queued">queued</option>
          <option value="running">running</option>
          <option value="succeeded">succeeded</option>
          <option value="failed">failed</option>
        </select>
      </Field>
      <Field label="Tag">
        <select value={state.tagFilter} onChange={(event) => onChange({ ...state, tagFilter: event.target.value })}>
          <option value="all">all</option>
          {options.tags.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Created from">
        <input
          type="datetime-local"
          value={state.createdFrom}
          onChange={(event) => onChange({ ...state, createdFrom: event.target.value })}
        />
      </Field>
      <Field label="Created to">
        <input
          type="datetime-local"
          value={state.createdTo}
          onChange={(event) => onChange({ ...state, createdTo: event.target.value })}
        />
      </Field>
      <Field label="Search" wide>
        <input
          value={state.query}
          onChange={(event) => onChange({ ...state, query: event.target.value })}
          placeholder="summary, run id, project..."
        />
      </Field>
    </div>
  );
}

