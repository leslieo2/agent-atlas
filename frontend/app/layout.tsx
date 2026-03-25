import type { Metadata } from "next";
import { ReactNode } from "react";
import WorkbenchShell from "@/src/widgets/workbench-shell/WorkbenchShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent Flight Recorder",
  description: "Agent Infra Workbench for trajectory replay, evaluation, and export."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <WorkbenchShell>{children}</WorkbenchShell>
      </body>
    </html>
  );
}
