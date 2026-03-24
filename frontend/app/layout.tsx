import type { Metadata } from "next";
import { ReactNode } from "react";
import "../app/globals.css";

export const metadata: Metadata = {
  title: "Agent Flight Recorder",
  description: "Agent Infra Workbench for trajectory replay, evaluation, and export."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
