import { useEffect, useState } from "react";
import { getBuilds } from "../lib/api";

export default function Builds() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await getBuilds();
      setRows(data);
      setErr(null);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "Failed to load builds");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Builds</h3>
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
                <th className="text-left p-2">App</th>
                <th className="text-left p-2">Status</th>
                <th className="text-left p-2">Created</th>
                <th className="text-left p-2">Finished</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((b) => (
                <tr key={b.id} className="border-t border-slate-800">
                  <td className="p-2">{b.id}</td>
                  <td className="p-2">{b.app_id}</td>
                  <td className="p-2">{b.status}</td>
                  <td className="p-2">{b.created_at}</td>
                  <td className="p-2">{b.finished_at || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}