import { useEffect, useState } from "react";
import { getAuditLogs } from "../lib/api";

export default function Audit() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await getAuditLogs();
      setRows(data);
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
        <h3 className="font-semibold">Audit Logs</h3>
        <button onClick={refresh} className="px-3 py-1.5 rounded bg-slate-800 border border-slate-700 text-sm">Refresh</button>
      </div>
      {loading ? (
        <div className="text-sm text-slate-400">Loading...</div>
      ) : (
        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead className="text-slate-400">
              <tr>
                <th className="text-left p-2">Time</th>
                <th className="text-left p-2">Actor</th>
                <th className="text-left p-2">Action</th>
                <th className="text-left p-2">Target</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id} className="border-t border-slate-800">
                  <td className="p-2">{a.timestamp}</td>
                  <td className="p-2">{a.actor}</td>
                  <td className="p-2">{a.action}</td>
                  <td className="p-2">{a.target_type}:{a.target_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}