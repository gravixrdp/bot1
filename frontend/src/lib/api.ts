import axios from "axios";

axios.defaults.withCredentials = true;

// Set CSRF token header from cookie on mutating requests
axios.interceptors.request.use((config) => {
  const method = (config.method || "get").toLowerCase();
  if (["post", "put", "patch", "delete"].includes(method)) {
    const csrf = document.cookie
      .split(";")
      .map((s) => s.trim())
      .find((c) => c.startsWith("gravix_csrf="));
    if (csrf) {
      config.headers = config.headers || {};
      config.headers["x-csrf-token"] = csrf.split("=")[1];
    }
  }
  return config;
});

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

export async function listUsers() {
  const res = await axios.get("/api/users");
  return res.data as Array<any>;
}

export async function grantPremium(userId: number, days: number) {
  const res = await axios.post(`/api/users/${userId}/grant`, { days });
  return res.data;
}

export async function revokePremium(userId: number) {
  const res = await axios.post(`/api/users/${userId}/revoke`);
  return res.data;
}

export async function listContainers() {
  const res = await axios.get("/api/containers");
  return res.data as Array<any>;
}

export async function containerAction(cid: string, action: "start" | "stop" | "restart" | "delete") {
  const res = await axios.post(`/api/containers/${cid}/action`, { action });
  return res.data;
}

export async function getBuilds() {
  const res = await axios.get("/api/builds");
  return res.data as Array<any>;
}

export async function getTickets() {
  const res = await axios.get("/api/support/tickets");
  return res.data as Array<any>;
}

export async function replyTicket(tid: number, message: string) {
  const params = new URLSearchParams({ message });
  const res = await axios.post(`/api/support/tickets/${tid}/reply?${params.toString()}`);
  return res.data;
}

export async function postBroadcast(scope: string, message: string, user_ids?: number[]) {
  const res = await axios.post("/api/broadcast", { scope, message, user_ids });
  return res.data;
}

export async function getAuditLogs() {
  const res = await axios.get("/api/audit");
  return res.data as Array<any>;
}

export async function changePassword(current_password: string, new_password: string) {
  const res = await axios.post("/api/auth/password", { current_password, new_password });
  return res.data;
}