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
  const openFilePicker = () => {
    const input = fileInputRef.current as (HTMLInputElement & { showPicker?: () => void }) | null;
    if (!input) {
      return;
    }

    if (typeof input.showPicker === "function") {
      input.showPicker();
      return;
    }

    input.click();
  };

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".jsonl"
        aria-label="Upload dataset JSONL"
        style={{
          position: "absolute",
          width: 1,
          height: 1,
          padding: 0,
          margin: -1,
          overflow: "hidden",
          clip: "rect(0, 0, 0, 0)",
          whiteSpace: "nowrap",
          border: 0
        }}
        onChange={onChange}
      />
      <Button onClick={openFilePicker}>Upload JSONL</Button>
    </>
  );
}
