import { useState } from "react";
import { changePassword } from "../lib/api";

export default function Settings() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg(null); setErr(null);
    if (next !== confirm) { setErr("Passwords do not match"); return; }
    try {
      await changePassword(current, next);
      setMsg("Password changed");
      setCurrent(""); setNext(""); setConfirm("");
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "Failed to change password");
    }
  };

  return (
    <form onSubmit={submit} className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
      <h3 className="font-semibold">Settings</h3>
      <div>
        <label className="block text-sm mb-1">Current password</label>
        <input type="password" className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700" value={current} onChange={(e)=>setCurrent(e.target.value)} />
      </div>
      <div>
        <label className="block text-sm mb-1">New password</label>
        <input type="password" className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700" value={next} onChange={(e)=>setNext(e.target.value)} />
      </div>
      <div>
        <label className="block text-sm mb-1">Confirm new password</label>
        <input type="password" className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700" value={confirm} onChange={(e)=>setConfirm(e.target.value)} />
      </div>
      {msg && <div className="text-green-400 text-sm">{msg}</div>}
      {err && <div className="text-red-400 text-sm">{err}</div>}
      <button className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-semibold">Update Password</button>
    </form>
  );
}