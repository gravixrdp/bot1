import { useEffect, useState } from "react";
import { containerAction, listContainers } from "../lib/api";

export default function Containers() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await listContainers();
      setRows(data);
      setErr(null);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "Failed to load containers");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const act = async (id: string, action: "start" | "stop" | "restart" | "delete") => {
    await containerAction(id, action);
    refresh();
  };

  return (
    <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Containers</h3>
        <button onClick={refresh} className="px-3 py-1.5 rounded bg-slate-800 border border-slate-700 text-sm">
          Refresh
        </button>
      </div>
      {loading ? (
        <div className="text-sm text-slate-400">Loading...</div>
      ) : err ? (
        <div className="text-sm text-red-400">{err}</div>
      ) : (
        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead className="text-slate-400">
              <tr>
                <th className="text-left p-2">ID</th>
                <th className="text-left p-2">User</th>
                <th className="text-left p-2">Name</th>
                <th className="text-left p-2">Status</th>
                <th className="text-left p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id} className="border-t border-slate-800">
                  <td className="p-2">{c.id}</td>
                  <td className="p-2">{c.user_id}</td>
                  <td className="p-2">{c.name}</td>
                  <td className="p-2">{c.status}</td>
                  <td className="p-2 space-x-2">
                    <button onClick={() => act(c.id, "start")} className="px-2 py-1 rounded bg-indigo-600 hover:bg-indigo-500">Start</button>
                    <button onClick={() => act(c.id, "stop")} className="px-2 py-1 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700">Stop</button>
                    <button onClick={() => act(c.id, "restart")} className="px-2 py-1 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700">Restart</button>
                    <button onClick={() => act(c.id, "delete")} className="px-2 py-1 rounded bg-red-600 hover:bg-red-500">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}