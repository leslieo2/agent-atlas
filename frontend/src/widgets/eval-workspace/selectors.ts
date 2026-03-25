import type { EvalResult } from "@/src/entities/eval/model";

export function getEvalTotals(rows: EvalResult[]) {
  if (!rows.length) {
    return { successRate: 0, toolSuccessRate: 0, latencyMs: 0, tokenUsage: 0, judgeScore: 0 };
  }

  const passCount = rows.filter((row) => row.status === "pass").length;
  const avgScore = rows.reduce((acc, row) => acc + row.score, 0) / rows.length;

  return {
    successRate: Math.round((passCount / rows.length) * 100),
    toolSuccessRate: Math.round((passCount / rows.length) * 100),
    latencyMs: 0,
    tokenUsage: 0,
    judgeScore: Number(avgScore.toFixed(2))
  };
}

export function getVisibleEvalRows(rows: EvalResult[], query: string, failuresOnly: boolean) {
  return rows.filter((row) => {
    const matchesQuery = row.runId.includes(query) || row.sampleId.includes(query);
    const matchesFailureToggle = !failuresOnly || row.status === "fail";
    return matchesQuery && matchesFailureToggle;
  });
}

