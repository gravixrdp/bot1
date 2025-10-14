import { ReactNode } from "react";

export type NavKey = "dashboard" | "users" | "containers" | "builds" | "support" | "broadcast" | "audit" | "settings";

export default function Sidebar({
  active,
  onNavigate,
  children,
}: {
  active: NavKey;
  onNavigate: (k: NavKey) => void;
  children?: ReactNode;
}) {
  const items: Array<{ key: NavKey; label: string; icon: string }> = [
    { key: "dashboard", label: "Dashboard", icon: "🏠" },
    { key: "users", label: "Users", icon: "👥" },
    { key: "containers", label: "Containers", icon: "📦" },
    { key: "builds", label: "Builds", icon: "🔧" },
    { key: "support", label: "Support", icon: "🆘" },
    { key: "broadcast", label: "Broadcast", icon: "📣" },
    { key: "audit", label: "Audit Logs", icon: "🧾" },
    { key: "settings", label: "Settings", icon: "⚙️" },
  ];

  return (
    <aside className="hidden md:flex md:flex-col w-64 bg-gradient-to-b from-slate-950 to-slate-900 border-r border-slate-800">
      <div className="px-5 py-4 text-xl font-bold tracking-wide">
        <span className="text-indigo-400">GRAVIX</span>
      </div>
      <nav className="flex-1 px-2 space-y-1">
        {items.map((it) => (
          <button
            key={it.key}
            onClick={() => onNavigate(it.key)}
            className={`w-full text-left flex items-center gap-3 px-3 py-2 rounded-lg transition ${
              active === it.key
                ? "bg-slate-800/80 text-white"
                : "text-slate-300 hover:bg-slate-800/70 hover:text-white"
            }`}
          >
            <span className="text-lg">{it.icon}</span>
            <span className="font-medium">{it.label}</span>
          </button>
        ))}
      </nav>
      {children}
      <div className="px-4 py-4 text-xs text-slate-500">v0.1.0</div>
    </aside>
  );
}