"use client";

import type { ChangeEvent, MutableRefObject } from "react";
import { Button } from "@/src/shared/ui/Button";

export function DatasetUpload({
  fileInputRef,
  onChange
}: {
  fileInputRef: MutableRefObject<HTMLInputElement | null>;
  onChange: (event: ChangeEvent<HTMLInputElement>) => Promise<void>;
}) {
  return (
    <>
      <input ref={fileInputRef} type="file" accept=".jsonl" style={{ display: "none" }} onChange={onChange} />
      <Button onClick={() => fileInputRef.current?.click()}>Upload JSONL</Button>
    </>
  );
}
