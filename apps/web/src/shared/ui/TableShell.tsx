import type { ReactNode } from "react";
import styles from "./TableShell.module.css";

export function TableShell({ children, plain = false }: { children: ReactNode; plain?: boolean }) {
  return <div className={[styles.shell, plain ? styles.plain : styles.deep].filter(Boolean).join(" ")}>{children}</div>;
}
