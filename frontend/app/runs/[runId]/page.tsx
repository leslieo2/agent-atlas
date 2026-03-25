import TrajectoryWorkspace from "@/src/widgets/trajectory-workspace/TrajectoryWorkspace";

export default function RunTrajectoryPage({ params }: { params: { runId: string } }) {
  return <TrajectoryWorkspace runId={params.runId} />;
}
