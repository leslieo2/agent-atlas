import EvalWorkspace from "@/src/widgets/eval-workspace/EvalWorkspace";

export default function EvalsPage({
  searchParams
}: {
  searchParams?: { runIds?: string; dataset?: string };
}) {
  const initialRunIds = searchParams?.runIds?.split(",").filter(Boolean) ?? [];
  return <EvalWorkspace initialRunIds={initialRunIds} initialDataset={searchParams?.dataset} />;
}
