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

export function getRunEvalSummaries(rows: EvalResult[]) {
  const grouped = new Map<
    string,
    {
      runId: string;
      total: number;
      passCount: number;
      averageScore: number;
    }
  >();

  rows.forEach((row) => {
    const current = grouped.get(row.runId) ?? {
      runId: row.runId,
      total: 0,
      passCount: 0,
      averageScore: 0
    };
    current.total += 1;
    if (row.status === "pass") {
      current.passCount += 1;
    }
    current.averageScore += row.score;
    grouped.set(row.runId, current);
  });

  return Array.from(grouped.values())
    .map((summary) => ({
      runId: summary.runId,
      total: summary.total,
      passCount: summary.passCount,
      failCount: summary.total - summary.passCount,
      successRate: summary.total ? Math.round((summary.passCount / summary.total) * 100) : 0,
      averageScore: summary.total ? Number((summary.averageScore / summary.total).toFixed(2)) : 0
    }))
    .sort((left, right) => right.successRate - left.successRate || right.averageScore - left.averageScore);
}
