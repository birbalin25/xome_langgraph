import { Home, LayoutDashboard, MessageSquare } from "lucide-react";

interface HeaderProps {
  view: "dashboard" | "chat";
  onViewChange: (view: "dashboard" | "chat") => void;
}

export default function Header({ view, onViewChange }: HeaderProps) {
  return (
    <header className="bg-xome-900 text-white shadow-lg">
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <Home className="h-7 w-7 text-xome-400" />
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              Xome Campaign Platform
            </h1>
            <p className="text-xs text-xome-300">
              Personalized email campaigns for high-intent buyers
            </p>
          </div>
        </div>

        {/* View toggle */}
        <div className="flex rounded-lg bg-xome-800 p-1">
          <button
            onClick={() => onViewChange("dashboard")}
            className={`flex items-center gap-2 rounded-md px-4 py-1.5 text-sm font-medium transition ${
              view === "dashboard"
                ? "bg-xome-600 text-white"
                : "text-xome-300 hover:text-white"
            }`}
          >
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </button>
          <button
            onClick={() => onViewChange("chat")}
            className={`flex items-center gap-2 rounded-md px-4 py-1.5 text-sm font-medium transition ${
              view === "chat"
                ? "bg-xome-600 text-white"
                : "text-xome-300 hover:text-white"
            }`}
          >
            <MessageSquare className="h-4 w-4" />
            Chat
          </button>
        </div>
      </div>
    </header>
  );
}
