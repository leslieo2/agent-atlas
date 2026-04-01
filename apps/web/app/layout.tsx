import type { Metadata } from "next";
import type { CSSProperties, ReactNode } from "react";
import { FrontendQueryProvider } from "@/src/shared/query/provider";
import WorkbenchShell from "@/src/widgets/workbench-shell/WorkbenchShell";
import "./globals.css";

const fontVariables = {
  "--font-sans":
    '"Manrope", "Avenir Next", "Segoe UI", "Helvetica Neue", Arial, sans-serif',
  "--font-display":
    '"Space Grotesk", "Avenir Next Condensed", "Segoe UI", "Helvetica Neue", Arial, sans-serif',
  "--font-mono":
    '"IBM Plex Mono", "SFMono-Regular", "SF Mono", Consolas, "Liberation Mono", monospace'
} as CSSProperties;

export const metadata: Metadata = {
  title: "Agent Atlas",
  description: "An RL-oriented control plane and evidence plane for agents, datasets, experiments, and exports."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={fontVariables}>
        <FrontendQueryProvider>
          <WorkbenchShell>{children}</WorkbenchShell>
        </FrontendQueryProvider>
      </body>
    </html>
  );
}
