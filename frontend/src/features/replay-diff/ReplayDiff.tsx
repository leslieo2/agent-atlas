"use client";

import { DiffEditor } from "@monaco-editor/react";

type Props = {
  original: string;
  modified: string;
  lastDiff: string;
};

export function ReplayDiff({ original, modified, lastDiff }: Props) {
  return (
    <>
      <DiffEditor
        original={original}
        modified={modified}
        language="json"
        height="320px"
        options={{
          renderSideBySide: true,
          readOnly: false,
          minimap: { enabled: false },
          fontSize: 12
        }}
      />
      <p className="muted-note" style={{ marginTop: 8 }}>
        Replay diff: {lastDiff}
      </p>
    </>
  );
}

