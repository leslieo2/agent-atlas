"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Airplay, ClipboardList, Cpu, RefreshCcw } from "lucide-react";
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
    href: "/replay",
    label: "Replay",
    description: "Patch a single step and compare output diffs quickly.",
    icon: RefreshCcw,
    match: (pathname: string) => pathname === "/replay" || pathname.includes("/replay")
  },
  {
    href: "/evals",
    label: "Evals",
    description: "Run datasets, compare samples, and drill into failures.",
    icon: ClipboardList,
    match: (pathname: string) => pathname.startsWith("/evals")
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

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.eyebrow}>Observability and replay</span>
          <h1>Agent Flight Recorder</h1>
          <p>Inspect runs, replay steps, benchmark datasets, and export trace artifacts from one place.</p>
        </div>

        <nav className={styles.nav} aria-label="Primary">
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
        </nav>

      </aside>
      <main className={styles.content}>{children}</main>
    </div>
  );
}
