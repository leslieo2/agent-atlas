import type { Metadata } from "next";
import { ReactNode } from "react";
import { FrontendQueryProvider } from "@/src/shared/query/provider";
import WorkbenchShell from "@/src/widgets/workbench-shell/WorkbenchShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent Flight Recorder",
  description: "Agent Infra Workbench for discovery, execution, trajectory inspection, and export."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <FrontendQueryProvider>
          <WorkbenchShell>{children}</WorkbenchShell>
        </FrontendQueryProvider>
      </body>
    </html>
  );
}
