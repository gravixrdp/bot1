import { useEffect, useState } from "react";
import { grantPremium, listUsers, revokePremium } from "../lib/api";

export default function Users() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await listUsers();
      setRows(data);
      setErr(null);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "Failed to load users");
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
        <h3 className="font-semibold">Users</h3>
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
                <th className="text-left p-2">Username</th>
                <th className="text-left p-2">Premium</th>
                <th className="text-left p-2">Expiry</th>
                <th className="text-left p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((u) => (
                <tr key={u.id} className="border-t border-slate-800">
                  <td className="p-2">{u.id}</td>
                  <td className="p-2">{u.username || "-"}</td>
                  <td className="p-2">{u.is_premium ? "Yes" : "No"}</td>
                  <td className="p-2">{u.premium_expires || "-"}</td>
                  <td className="p-2 space-x-2">
                    <button
                      onClick={async () => {
                        await grantPremium(u.id, 30);
                        refresh();
                      }}
                      className="px-2 py-1 rounded bg-indigo-600 hover:bg-indigo-500"
                    >
                      Grant 30d
                    </button>
                    <button
                      onClick={async () => {
                        await revokePremium(u.id);
                        refresh();
                      }}
                      className="px-2 py-1 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700"
                    >
                      Revoke
                    </button>
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