import PlaygroundWorkspace from "@/src/widgets/playground-workspace/PlaygroundWorkspace";

export default function PlaygroundPage({
  searchParams
}: {
  searchParams: { dataset?: string; agent?: string };
}) {
  return <PlaygroundWorkspace initialDataset={searchParams.dataset} initialAgentId={searchParams.agent} />;
}
