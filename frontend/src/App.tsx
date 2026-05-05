import { useState } from "react";
import Header from "./components/layout/Header";
import AppShell from "./components/layout/AppShell";
import ChatPanel from "./components/chat/ChatPanel";

export default function App() {
  const [view, setView] = useState<"dashboard" | "chat">("dashboard");

  return (
    <div className="flex h-screen flex-col">
      <Header view={view} onViewChange={setView} />
      {view === "dashboard" ? <AppShell /> : <ChatPanel />}
    </div>
  );
}
