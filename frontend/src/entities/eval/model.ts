export interface EvalResult {
  sampleId: string;
  runId: string;
  input: string;
  status: "pass" | "fail" | "running";
  score: number;
  reason?: string | null;
}

export interface EvalJob {
  jobId: string;
  runIds: string[];
  dataset: string;
  status: string;
  results: EvalResult[];
  createdAt: string;
}

export interface CreateEvalJobInput {
  runIds: string[];
  dataset: string;
  evaluators?: string[];
}

