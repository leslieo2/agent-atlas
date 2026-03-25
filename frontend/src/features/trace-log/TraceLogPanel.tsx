"use client";

export function TraceLogPanel({ log }: { log: string }) {
  return <pre className="output-log mono output-log-tall">{log}</pre>;
}

