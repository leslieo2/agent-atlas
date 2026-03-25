import ReplayWorkspace from "@/src/widgets/replay-workspace/ReplayWorkspace";

export default function RunReplayPage({
  params,
  searchParams
}: {
  params: { runId: string };
  searchParams: { stepId?: string };
}) {
  return <ReplayWorkspace runId={params.runId} initialStepId={searchParams.stepId} />;
}
