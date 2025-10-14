import { useState } from "react";
import { postBroadcast } from "../lib/api";

export default function Broadcast() {
  const [scope, setScope] = useState<"all" | "premium" | "user_ids">("all");
  const [message, setMessage] = useState("");
  const [userIds, setUserIds] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const ids = scope === "user_ids" ? userIds.split(",").map((s) => parseInt(s.trim(), 10)).filter(Boolean) : undefined;
    await postBroadcast(scope, message, ids);
    setMessage("");
    setUserIds("");
    alert("Broadcast queued");
  };

  return (
    <form onSubmit={submit} className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
      <h3 className="font-semibold">Broadcast</h3>
      <div>
        <label className="block text-sm mb-1">Scope</label>
        <select
          className="px-3 py-2 rounded-lg bg-slate-800 border border-slate-700"
          value={scope}
          onChange={(e) => setScope(e.target.value as any)}
        >
          <option value="all">All</option>
          <option value="premium">Premium</option>
          <option value="user_ids">Specific Users</option>
        </select>
      </div>
      {scope === "user_ids" && (
        <div>
          <label className="block text-sm mb-1">User IDs (comma separated)</label>
          <input
            className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700"
            value={userIds}
            onChange={(e) => setUserIds(e.target.value)}
          />
        </div>
      )}
      <div>
        <label className="block text-sm mb-1">Message</label>
        <textarea
          className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 h-32"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Your announcement..."
        />
      </div>
      <button className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-semibold">Send Broadcast</button>
    </form>
  );
}