import type { HTMLAttributes, ReactNode } from "react";
import styles from "./Panel.module.css";

type Props = HTMLAttributes<HTMLElement> & {
  as?: "section" | "aside" | "div";
  children: ReactNode;
  tone?: "default" | "strong" | "plain";
};

export function Panel({ as = "section", children, className, tone = "default", ...rest }: Props) {
  const Component = as;
  const toneClass = tone === "strong" ? styles.strong : tone === "plain" ? styles.plain : "";

  return (
    <Component className={[styles.panel, toneClass, className].filter(Boolean).join(" ")} {...rest}>
      {children}
    </Component>
  );
}

