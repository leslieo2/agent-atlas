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
    description: "Govern agent snapshots, provenance, and compatibility before experiments.",
    icon: Shapes,
    match: (pathname: string) => pathname.startsWith("/agents")
  },
  {
    href: "/datasets",
    label: "Datasets",
    description: "Control dataset slices, provenance, and export eligibility before eval.",
    icon: Database,
    match: (pathname: string) => pathname.startsWith("/datasets")
  },
  {
    href: "/experiments",
    label: "Experiments",
    description: "Create batch runs, compare baselines, and curate export-ready trajectory rows.",
    icon: Radar,
    match: (pathname: string) => pathname.startsWith("/experiments")
  },
  {
    href: "/exports",
    label: "Exports",
    description: "Package curated eval rows into offline RL handoff files.",
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
            <span className={styles.eyebrow}>Control plane + evidence plane</span>
          </div>
          <h1>Agent Atlas</h1>
          <p>
            Coordinate experiments and evidence in Atlas. Runner adapters such as Claude Code CLI stay visible but do
            not become the product center, and deep trace debugging stays in Phoenix.
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
          <div className={styles.boundaryNote}>
            <span className={styles.boundaryLabel}>Product boundary</span>
            <p>
              Atlas owns orchestration, evidence association, curation, and exports. External systems own runner and
              tracing internals.
            </p>
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
