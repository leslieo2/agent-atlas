import type { ReactNode } from "react";
import styles from "./MetricCard.module.css";

export function MetricCard({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className={styles.card}>
      <span className={styles.label}>{label}</span>
      <strong className={styles.value}>{value}</strong>
    </div>
  );
}

