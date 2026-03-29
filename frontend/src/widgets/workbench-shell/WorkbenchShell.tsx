"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Database, Download, Radar, Shapes } from "lucide-react";
import type { ReactNode } from "react";
import styles from "./WorkbenchShell.module.css";

const navItems = [
  {
    href: "/agents",
    label: "Agents",
    description: "Discover agents, publish governed snapshots, and inspect provenance.",
    icon: Shapes,
    match: (pathname: string) => pathname.startsWith("/agents")
  },
  {
    href: "/datasets",
    label: "Datasets",
    description: "Manage RL data assets, slices, tags, and sample-level export eligibility.",
    icon: Database,
    match: (pathname: string) => pathname.startsWith("/datasets")
  },
  {
    href: "/evals",
    label: "Evals",
    description: "Run batch evals, compare baseline vs candidate, and curate sample results.",
    icon: Radar,
    match: (pathname: string) => pathname.startsWith("/evals")
  },
  {
    href: "/exports",
    label: "Exports",
    description: "Build RL-ready export files from curated eval results and compare slices.",
    icon: Download,
    match: (pathname: string) => pathname.startsWith("/exports")
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
            Govern published agents, curate dataset-driven eval results, and ship RL-ready exports.
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
