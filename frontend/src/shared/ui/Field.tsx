import type { ReactNode } from "react";
import styles from "./Field.module.css";

export function Field({
  children,
  label,
  htmlFor,
  wide = false
}: {
  children: ReactNode;
  label: string;
  htmlFor?: string;
  wide?: boolean;
}) {
  return (
    <div className={[styles.field, wide ? styles.wide : ""].filter(Boolean).join(" ")}>
      <label className={styles.label} htmlFor={htmlFor}>
        {label}
      </label>
      {children}
    </div>
  );
}

