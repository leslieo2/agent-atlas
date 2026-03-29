import ExportsWorkspace from "@/src/widgets/exports-workspace/ExportsWorkspace";

export default function ExportsPage({
  searchParams
}: {
  searchParams: { eval?: string; baseline?: string; candidate?: string };
}) {
  return (
    <ExportsWorkspace
      initialEvalJobId={searchParams.eval}
      initialBaselineEvalJobId={searchParams.baseline}
      initialCandidateEvalJobId={searchParams.candidate}
    />
  );
}
