export default function Topbar({ onLogout }: { onLogout: () => void }) {
  return (
    <header className="h-16 flex items-center justify-between px-4 md:px-6 border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0">
      <div className="md:hidden font-bold text-lg">
        <span className="text-indigo-400">GRAVIX</span>
      </div>
      <div className="hidden md:block text-sm text-slate-400">
        Premium Admin Dashboard
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={() => {
            fetch("/api/auth/logout", { method: "POST", credentials: "include" }).then(() => onLogout());
          }}
          className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 hover:bg-slate-700 text-sm"
        >
          Logout
        </button>
      </div>
    </header>
  );
}