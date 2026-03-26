"use client";

import { StatusPill } from "@/src/shared/ui/StatusPill";

type Tone = "success" | "warn" | "error";

type Props = {
  tone: Tone;
  title: string;
  detail?: string;
  downloadHref?: string;
  downloadLabel?: string;
};

const statusCopy: Record<Tone, string> = {
  success: "Ready",
  warn: "Exporting",
  error: "Failed"
};

export function ArtifactExportFeedback({ tone, title, detail, downloadHref, downloadLabel }: Props) {
  return (
    <div
      className={["action-feedback", tone].join(" ")}
      role={tone === "error" ? "alert" : "status"}
      aria-live={tone === "error" ? "assertive" : "polite"}
    >
      <div className="action-feedback-row">
        <div className="action-feedback-copy">
          <div className="action-feedback-header">
            <StatusPill tone={tone}>{statusCopy[tone]}</StatusPill>
            <p className="action-feedback-title">{title}</p>
          </div>
          {detail ? <p className="action-feedback-detail">{detail}</p> : null}
        </div>
        {downloadHref && downloadLabel ? (
          <a className="text-link" href={downloadHref} target="_blank" rel="noreferrer">
            {downloadLabel}
          </a>
        ) : null}
      </div>
    </div>
  );
}
