import type { ReactNode } from "react";

interface SidebarProps {
  children: ReactNode;
}

export default function Sidebar({ children }: SidebarProps) {
  return (
    <aside className="w-72 shrink-0 overflow-y-auto border-r border-gray-200 bg-white p-5">
      {children}
    </aside>
  );
}
