export function Notice({ children, className }: { children: string; className?: string }) {
  return <p className={["muted-note", className].filter(Boolean).join(" ")}>{children}</p>;
}
