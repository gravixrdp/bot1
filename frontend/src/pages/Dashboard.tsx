import { useEffect, useRef, useState } from "react";
import { getStats } from "../lib/api";
import { connectAdminWS } from "../lib/ws";

export default function Dashboard({ onLogout }: { onLogout: () => void }) {
  const [stats, setStats] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    getStats().then(setStats);

    wsRef.current = connectAdminWS((msg) => {
      setEvents((prev) => [msg, ...prev].slice(0, 50));
    });
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return (
    <div className="min-h-screen">
      <header className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60 backdrop-blur">
        <div className="font-bold text-xl">
          <span className="text-indigo-400">GRAVIX</span> Admin
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => {
              fetch("/api/auth/logout", { method: "POST", credentials: "include" }).then(() => onLogout());
            }}
            className="px-3 py-1 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="p-6 grid gap-6 md:grid-cols-3">
        <div className="md:col-span-2 grid gap-6 md:grid-cols-2">
          <StatCard title="Total Users" value={stats?.total_users ?? 0} />
          <StatCard title="Premium Users" value={stats?.premium_users ?? 0} />
          <StatCard title="Active Containers" value={stats?.active_containers ?? 0} />
          <StatCard title="Running Builds" value={stats?.running_builds ?? 0} />
        </div>
        <div className="space-y-4">
          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
            <h3 className="font-semibold mb-2">System</h3>
            <div className="grid grid-cols-3 gap-2 text-sm">
              <Metric label="CPU" value={`${stats?.cpu_percent ?? 0}%`} />
              <Metric label="Memory" value={`${stats?.mem_percent ?? 0}%`} />
              <Metric label="Disk" value={`${stats?.disk_percent ?? 0}%`} />
            </div>
          </div>
          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
            <h3 className="font-semibold mb-2">Live Events</h3>
            <div className="h-64 overflow-auto text-xs space-y-1">
              {events.map((e, i) => (
                <pre key={i} className="text-slate-300 whitespace-pre-wrap">{typeof e === "string" ? e : JSON.stringify(e)}</pre>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function StatCard({ title, value }: { title: string; value: number | string }) {
  return (
    <div className="p-4 rounded-xl bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 shadow">
      <div className="text-sm text-slate-400">{title}</div>
      <div className="text-3xl font-bold mt-2">{value}</div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="font-semibold">{value}</div>
    </div>
  );
}