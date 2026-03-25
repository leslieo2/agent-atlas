"use client";

import { Button } from "@/src/shared/ui/Button";

export function ComparePreviousRunAction({ onCompare }: { onCompare: () => Promise<void> }) {
  return (
    <Button variant="ghost" onClick={onCompare}>
      Diff with previous run
    </Button>
  );
}

