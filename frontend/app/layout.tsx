import type { Metadata } from "next";
import { IBM_Plex_Mono, Manrope, Space_Grotesk } from "next/font/google";
import { ReactNode } from "react";
import { FrontendQueryProvider } from "@/src/shared/query/provider";
import WorkbenchShell from "@/src/widgets/workbench-shell/WorkbenchShell";
import "./globals.css";

const sans = Manrope({
  subsets: ["latin"],
  variable: "--font-sans"
});

const display = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display"
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono"
});

export const metadata: Metadata = {
  title: "Agent Atlas",
  description: "A local-first execution workbench for agents, runs, traces, and trajectories."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${display.variable} ${mono.variable}`}>
        <FrontendQueryProvider>
          <WorkbenchShell>{children}</WorkbenchShell>
        </FrontendQueryProvider>
      </body>
    </html>
  );
}
