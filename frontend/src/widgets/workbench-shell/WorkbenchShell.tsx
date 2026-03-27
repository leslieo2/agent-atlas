"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Airplay, Cpu, Database, Radar, Shapes } from "lucide-react";
import type { ReactNode } from "react";
import styles from "./WorkbenchShell.module.css";

const navItems = [
  {
    href: "/runs",
    label: "Runs",
    description: "Search executions, inspect status, and launch new work.",
    icon: Airplay,
    match: (pathname: string) => pathname === "/runs" || pathname.startsWith("/runs/")
  },
  {
    href: "/agents",
    label: "Agents",
    description: "Discover plugins, publish runnable snapshots, and inspect validation state.",
    icon: Shapes,
    match: (pathname: string) => pathname.startsWith("/agents")
  },
  {
    href: "/evals",
    label: "Evals",
    description: "Launch dataset batches, review aggregate regressions, and inspect failing samples.",
    icon: Radar,
    match: (pathname: string) => pathname.startsWith("/evals")
  },
  {
    href: "/datasets",
    label: "Datasets",
    description: "Import, inspect, and prepare datasets for evals and playground runs.",
    icon: Database,
    match: (pathname: string) => pathname.startsWith("/datasets")
  },
  {
    href: "/playground",
    label: "Playground",
    description: "Trigger manual runs and open fresh traces.",
    icon: Cpu,
    match: (pathname: string) => pathname.startsWith("/playground")
  }
] as const;

export default function WorkbenchShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const activeItem = navItems.find((item) => item.match(pathname)) ?? navItems[0];

  return (
    <div className={styles.shell}>
      <motion.aside
        className={styles.sidebar}
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        <div className={styles.brand}>
          <div className={styles.brandRow}>
            <span className={styles.brandBadge}>AA</span>
            <span className={styles.eyebrow}>Execution atlas</span>
          </div>
          <h1>Agent Atlas</h1>
          <p>
            Operate discovery, execution, trajectory review, and artifact export from a single local-first workspace.
          </p>
        </div>

        <motion.nav
          className={styles.nav}
          aria-label="Primary"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.08, ease: "easeOut" }}
        >
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = item.match(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={styles.navLink}
                aria-current={active ? "page" : undefined}
              >
                <span className={styles.navLabel}>
                  <Icon size={16} />
                  {item.label}
                </span>
                <span className={styles.navDescription}>{item.description}</span>
              </Link>
            );
          })}
        </motion.nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.focusCard}>
            <span className={styles.focusLabel}>Current workspace</span>
            <strong>{activeItem.label}</strong>
            <p>{activeItem.description}</p>
          </div>
        </div>
      </motion.aside>
      <motion.main
        className={styles.content}
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.1, ease: "easeOut" }}
      >
        {children}
      </motion.main>
    </div>
  );
}
