import ExportsWorkspace from "@/src/widgets/exports-workspace/ExportsWorkspace";

export default function ExportsPage({
  searchParams
}: {
  searchParams: { experiment?: string; baseline?: string; candidate?: string };
}) {
  return (
    <ExportsWorkspace
      initialExperimentId={searchParams.experiment}
      initialBaselineExperimentId={searchParams.baseline}
      initialCandidateExperimentId={searchParams.candidate}
    />
  );
}
