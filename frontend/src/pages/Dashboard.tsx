import { useEffect, useRef, useState } from "react";
import { getStats } from "../lib/api";
import { connectAdminWS } from "../lib/ws";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";

export default function Dashboard({ onLogout }: { onLogout: () => void }) {
  const [stats, setStats] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    getStats().then(setStats);

    wsRef.current = connectAdminWS((msg) => {
      setEvents((prev) => [msg, ...prev].slice(0, 80));
    });
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900 text-slate-100">
      <div className="flex">
        <Sidebar />
        <div className="flex-1 min-w-0">
          <Topbar onLogout={onLogout} />
          <main className="p-6">
            <div className="grid gap-6 md:grid-cols-12">
              <div className="md:col-span-9 grid gap-6 sm:grid-cols-2">
                <StatCard title="Total Users" value={stats?.total_users ?? 0} />
                <StatCard title="Premium Users" value={stats?.premium_users ?? 0} />
                <StatCard title="Active Containers" value={stats?.active_containers ?? 0} />
                <StatCard title="Running Builds" value={stats?.running_builds ?? 0} />
              </div>
              <div className="md:col-span-3 space-y-4">
                <Card>
                  <h3 className="font-semibold mb-3">System</h3>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <Metric label="CPU" value={`${stats?.cpu_percent ?? 0}%`} />
                    <Metric label="Memory" value={`${stats?.mem_percent ?? 0}%`} />
                    <Metric label="Disk" value={`${stats?.disk_percent ?? 0}%`} />
                  </div>
                </Card>
              </div>
            </div>

            <div className="mt-6 grid gap-6 md:grid-cols-2">
              <Card>
                <h3 className="font-semibold mb-3">Live Events</h3>
                <div className="h-80 overflow-auto text-xs space-y-1 custom-scroll">
                  {events.map((e, i) => (
                    <pre key={i} className="text-slate-300 whitespace-pre-wrap">{typeof e === "string" ? e : JSON.stringify(e)}</pre>
                  ))}
                </div>
              </Card>
              <Card>
                <h3 className="font-semibold mb-3">Alerts</h3>
                <div className="text-sm text-slate-400">No critical alerts</div>
              </Card>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-[0_0_0_1px_rgba(255,255,255,0.02)]">
      {children}
    </div>
  );
}

function StatCard({ title, value }: { title: string; value: number | string }) {
  return (
    <div className="p-5 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700/70 shadow-lg">
      <div className="text-sm text-slate-400">{title}</div>
      <div className="text-4xl font-extrabold mt-2 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-amber-300">
        {value}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="font-semibold">{value}</div>
    </div>
  );
}