export function connectAdminWS(onMessage: (msg: any) => void) {
  const ws = new WebSocket(
    (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws/admin"
  );
  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      onMessage(data);
    } catch {
      onMessage(ev.data);
    }
  };
  return ws;
}