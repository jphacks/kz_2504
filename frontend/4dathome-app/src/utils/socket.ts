import type { WSIn, WSOut } from "../types/session";

const WS_BASE =
  import.meta.env.VITE_WS_URL ||
  (location.protocol === "https:" ? "wss://" : "ws://") + location.host;

export class SessionSocket {
  private ws: WebSocket | null = null;

  constructor(
    private sessionId: string,
    private onMessage: (m: WSIn) => void,
    private onOpen?: () => void,
    private onClose?: () => void
  ) {}

  connect() {
    // 例: wss://host/ws?session=XXXXX&role=web
    const url = `${WS_BASE}/ws?session=${encodeURIComponent(this.sessionId)}&role=web`;
    console.log("[session-socket] connecting", { url });
    this.ws = new WebSocket(url);
    this.ws.onopen = () => {
      console.log("[session-socket] open", { readyState: this.ws?.readyState });
      this.onOpen?.();
    };
    this.ws.onclose = (ev) => {
      console.log("[session-socket] close", { code: ev.code, reason: ev.reason, wasClean: ev.wasClean });
      this.onClose?.();
    };
    this.ws.onmessage = (e) => {
      try {
        const parsed = JSON.parse(e.data);
        console.log("[session-socket] message", parsed);
        this.onMessage(parsed);
      } catch (err) {
        console.error("WS parse error", err);
      }
    };
    this.ws.onerror = (err) => {
      console.error("[session-socket] error", err);
    };
  }

  send(msg: WSOut) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const raw = JSON.stringify(msg);
      console.log("[session-socket] send", msg);
      this.ws.send(raw);
    }
  }

  close() {
    if (this.ws) {
      console.log("[session-socket] manual close");
      this.ws.close();
    }
  }
}
