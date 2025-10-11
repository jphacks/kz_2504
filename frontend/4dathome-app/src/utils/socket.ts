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
    this.ws = new WebSocket(url);
    this.ws.onopen = () => this.onOpen?.();
    this.ws.onclose = () => this.onClose?.();
    this.ws.onmessage = (e) => {
      try {
        this.onMessage(JSON.parse(e.data));
      } catch (err) {
        console.error("WS parse error", err);
      }
    };
  }

  send(msg: WSOut) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  close() { this.ws?.close(); }
}
