import axios from "axios";

axios.defaults.withCredentials = true;

export async function login(username: string, password: string) {
  const res = await axios.post("/api/auth/login", { username, password });
  return res.data;
}

export async function getMe() {
  const res = await axios.get("/api/auth/me");
  return res.data;
}

export async function getStats() {
  const res = await axios.get("/api/stats");
  return res.data as {
    total_users: number;
    premium_users: number;
    active_containers: number;
    running_builds: number;
    cpu_percent: number;
    mem_percent: number;
    disk_percent: number;
  };
}