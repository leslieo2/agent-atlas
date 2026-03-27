import EvalsWorkspace from "@/src/widgets/evals-workspace/EvalsWorkspace";

export default function EvalsPage({
  searchParams
}: {
  searchParams: { agent?: string; dataset?: string; job?: string };
}) {
  return (
    <EvalsWorkspace
      initialAgentId={searchParams.agent}
      initialDataset={searchParams.dataset}
      initialJobId={searchParams.job}
    />
  );
}
