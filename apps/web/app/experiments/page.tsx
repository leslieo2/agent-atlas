import ExperimentsWorkspace from "@/src/widgets/experiments-workspace/ExperimentsWorkspace";

export default function ExperimentsPage({
  searchParams
}: {
  searchParams: { agent?: string; datasetVersion?: string; experiment?: string };
}) {
  return (
    <ExperimentsWorkspace
      initialAgentId={searchParams.agent}
      initialDatasetVersionId={searchParams.datasetVersion}
      initialExperimentId={searchParams.experiment}
    />
  );
}
