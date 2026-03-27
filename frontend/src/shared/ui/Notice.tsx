import type { ReactNode } from "react";

export function Notice({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={["muted-note", className].filter(Boolean).join(" ")}>{children}</p>;
}
