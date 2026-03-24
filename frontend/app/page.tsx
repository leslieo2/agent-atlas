"use client";

import { useMemo, useState } from "react";
import { Airplay, Boxes, ClipboardList, Cpu, RefreshCcw } from "lucide-react";
import EvalBench from "@/components/EvalBench";
import PlayGround from "@/components/Playground";
import RunDashboard from "@/components/RunDashboard";
import StepReplayPanel from "@/components/StepReplayPanel";
import TrajectoryViewer from "@/components/TrajectoryViewer";

type Tab = "dashboard" | "trajectory" | "replay" | "eval" | "playground";

const tabs: Array<{ key: Tab; title: string; icon: JSX.Element }> = [
  { key: "dashboard", title: "Run dashboard", icon: <Airplay size={14} /> },
  { key: "trajectory", title: "Trajectory viewer", icon: <Boxes size={14} /> },
  { key: "replay", title: "Step replay", icon: <RefreshCcw size={14} /> },
  { key: "eval", title: "Eval bench", icon: <ClipboardList size={14} /> },
  { key: "playground", title: "Playground", icon: <Cpu size={14} /> }
];

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");

  const body = useMemo(() => {
    switch (activeTab) {
      case "dashboard":
        return <RunDashboard />;
      case "trajectory":
        return <TrajectoryViewer />;
      case "replay":
        return <StepReplayPanel />;
      case "eval":
        return <EvalBench />;
      case "playground":
        return <PlayGround />;
      default:
        return <RunDashboard />;
    }
  }, [activeTab]);

  return (
    <div className="app-shell">
      <aside className="left-panel">
        <div className="left-brand">
          <h1>Agent Flight Recorder</h1>
          <p>Infra workbench for replay, evaluation, and trajectory export.</p>
        </div>
        <nav className="left-nav">
          {tabs.map((item) => (
            <button
              key={item.key}
              className={`nav-btn ${activeTab === item.key ? "active" : ""}`}
              onClick={() => setActiveTab(item.key)}
            >
              <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
                {item.icon} {item.title}
              </span>
            </button>
          ))}
        </nav>
      </aside>
      <main className="content">{body}</main>
    </div>
  );
}
