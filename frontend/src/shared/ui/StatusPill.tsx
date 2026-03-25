import styles from "./StatusPill.module.css";

type Tone = "success" | "warn" | "error";

export function StatusPill({ children, tone }: { children: string; tone: Tone }) {
  return <span className={[styles.pill, styles[tone]].join(" ")}>{children}</span>;
}

