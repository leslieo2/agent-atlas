import PlaygroundWorkspace from "@/src/widgets/playground-workspace/PlaygroundWorkspace";

export default function PlaygroundPage({
  searchParams
}: {
  searchParams: { dataset?: string; agent?: string; prompt?: string; tags?: string };
}) {
  return (
    <PlaygroundWorkspace
      initialDataset={searchParams.dataset}
      initialAgentId={searchParams.agent}
      initialPrompt={searchParams.prompt}
      initialTags={
        searchParams.tags
          ? searchParams.tags
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean)
          : undefined
      }
    />
  );
}
