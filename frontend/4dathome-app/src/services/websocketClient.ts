// src/services/websocketClient.ts
import { BACKEND_WS_URL } from "../config/backend";

type Handler = (data?: any) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<Handler>> = new Map();

  private join(base: string, path: string) {
    const b = base.replace(/\/$/, "");
    const p = path.startsWith("/") ? path : `/${path}`;
    return `${b}${p}`;
  }

  async connect(endpoint: string): Promise<void> {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return; // already connected/connecting
    }
    const url = this.join(BACKEND_WS_URL, endpoint);
    await new Promise<void>((resolve, reject) => {
      try {
        const ws = new WebSocket(url);
        this.ws = ws;
        ws.onopen = () => {
          this.emit("open");
          resolve();
        };
        ws.onmessage = (ev) => {
          let parsed: any = null;
          try { parsed = JSON.parse(ev.data as any); } catch { this.emit("message", ev.data); return; }
          if (parsed && typeof parsed.type === "string") {
            this.emit(parsed.type, parsed);
          }
          this.emit("message", parsed);
        };
        ws.onerror = (e) => { this.emit("error", e); };
        ws.onclose = (e) => { this.emit("close", e); };
      } catch (e) {
        reject(e);
      }
    });
  }

  isConnected() {
    return !!this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  send(obj: any) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) throw new Error("WebSocket not open");
    this.ws.send(JSON.stringify(obj));
  }

  disconnect() {
    try { this.ws?.close(); } catch {}
    this.ws = null;
  }

  on(event: string, handler: Handler) {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event)!.add(handler);
    return () => this.off(event, handler);
  }

  off(event: string, handler: Handler) {
    this.handlers.get(event)?.delete(handler);
  }

  private emit(event: string, data?: any) {
    this.handlers.get(event)?.forEach((h) => {
      try { h(data); } catch (e) { console.error("[ws] handler error", e); }
    });
  }
}
