import type { ReactNode } from "react";
import styles from "./TableShell.module.css";

export function TableShell({ children, plain = false }: { children: ReactNode; plain?: boolean }) {
  return <div className={[styles.shell, plain ? styles.plain : ""].filter(Boolean).join(" ")}>{children}</div>;
}

