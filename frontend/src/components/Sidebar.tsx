import { ReactNode } from "react";

export default function Sidebar({ children }: { children?: ReactNode }) {
  const items = [
    { label: "Dashboard", icon: "🏠" },
    { label: "Users", icon: "👥" },
    { label: "Containers", icon: "📦" },
    { label: "Builds", icon: "🔧" },
    { label: "Support", icon: "🆘" },
    { label: "Broadcast", icon: "📣" },
    { label: "Audit Logs", icon: "🧾" },
    { label: "Settings", icon: "⚙️" },
  ];

  return (
    <aside className="hidden md:flex md:flex-col w-64 bg-gradient-to-b from-slate-950 to-slate-900 border-r border-slate-800">
      <div className="px-5 py-4 text-xl font-bold tracking-wide">
        <span className="text-indigo-400">GRAVIX</span>
      </div>
      <nav className="flex-1 px-2 space-y-1">
        {items.map((it) => (
          <a
            key={it.label}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800/70 hover:text-white transition"
            href="#"
          >
            <span className="text-lg">{it.icon}</span>
            <span className="font-medium">{it.label}</span>
          </a>
        ))}
      </nav>
      {children}
      <div className="px-4 py-4 text-xs text-slate-500">v0.1.0</div>
    </aside>
  );
}