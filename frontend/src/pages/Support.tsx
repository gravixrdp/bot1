import { useEffect, useState } from "react";
import { getTickets, replyTicket } from "../lib/api";

export default function Support() {
  const [rows, setRows] = useState<any[]>([]);
  const [replyText, setReplyText] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await getTickets();
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
        <h3 className="font-semibold">Support Tickets</h3>
        <button onClick={refresh} className="px-3 py-1.5 rounded bg-slate-800 border border-slate-700 text-sm">
          Refresh
        </button>
      </div>
      {loading ? (
        <div className="text-sm text-slate-400">Loading...</div>
      ) : (
        <div className="space-y-3">
          {rows.map((t) => (
            <div key={t.id} className="p-4 rounded-xl border border-slate-800 bg-slate-900/70">
              <div className="text-sm text-slate-400 mb-2">Ticket #{t.id} • User {t.user_id} • {t.status}</div>
              <div className="flex gap-2">
                <input
                  className="flex-1 px-3 py-2 rounded-lg bg-slate-800 border border-slate-700"
                  placeholder="Type reply..."
                  value={replyText[t.id] || ""}
                  onChange={(e) => setReplyText({ ...replyText, [t.id]: e.target.value })}
                />
                <button
                  onClick={async () => {
                    const msg = (replyText[t.id] || "").trim();
                    if (!msg) return;
                    await replyTicket(t.id, msg);
                    setReplyText({ ...replyText, [t.id]: "" });
                  }}
                  className="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500"
                >
                  Send
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}