import { useEffect, useState } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Users from "./pages/Users";
import Containers from "./pages/Containers";
import Builds from "./pages/Builds";
import Support from "./pages/Support";
import Broadcast from "./pages/Broadcast";
import Audit from "./pages/Audit";
import Settings from "./pages/Settings";
import Sidebar, { NavKey } from "./components/Sidebar";
import Topbar from "./components/Topbar";
import { getMe } from "./lib/api";

export default function App() {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [page, setPage] = useState<NavKey>("dashboard");

  useEffect(() => {
    getMe().then(
      () => setAuthed(true),
      () => setAuthed(false)
    );
  }, []);

  if (authed === null) return null;

  if (!authed) {
    return <Login onSuccess={() => setAuthed(true)} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900 text-slate-100">
      <div className="flex">
        <Sidebar active={page} onNavigate={setPage} />
        <div className="flex-1 min-w-0">
          <Topbar onLogout={() => setAuthed(false)} />
          <main className="p-6 space-y-6">
            {page === "dashboard" && <Dashboard onLogout={() => setAuthed(false)} />}
            {page === "users" && <Users />}
            {page === "containers" && <Containers />}
            {page === "builds" && <Builds />}
            {page === "support" && <Support />}
            {page === "broadcast" && <Broadcast />}
            {page === "audit" && <Audit />}
            {page === "settings" && <Settings />}
          </main>
        </div>
      </div>
    </div>
  );
}