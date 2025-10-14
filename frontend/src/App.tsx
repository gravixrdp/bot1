import { useEffect, useState } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import { getMe } from "./lib/api";

export default function App() {
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    getMe().then(
      () => setAuthed(true),
      () => setAuthed(false)
    );
  }, []);

  if (authed === null) return null;

  return authed ? <Dashboard onLogout={() => setAuthed(false)} /> : <Login onSuccess={() => setAuthed(true)} />;
}