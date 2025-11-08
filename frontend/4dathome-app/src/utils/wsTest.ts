// Simple manual WebSocket connectivity test utility
// Usage (in console or temporary component):
//   import { runWsHandshakeTest } from './utils/wsTest';
//   runWsHandshakeTest('demo_session', 5000);

import { BACKEND_WS_URL } from "../config/backend";

interface WsTestResult {
  ok: boolean;
  phase: string;
  error?: string;
  elapsed_ms: number;
  received_connection_established: boolean;
}

export async function runWsHandshakeTest(sessionId: string, timeoutMs = 5000, hubId?: string): Promise<WsTestResult> {
  const started = performance.now();
  const url = hubId
    ? `${BACKEND_WS_URL}/api/playback/ws/sync/${encodeURIComponent(sessionId)}?hub=${encodeURIComponent(hubId)}`
    : `${BACKEND_WS_URL}/api/playback/ws/sync/${encodeURIComponent(sessionId)}`;
  let received = false;
  let ws: WebSocket | null = null;
  return await new Promise<WsTestResult>((resolve) => {
    let settled = false;
    const finish = (data: Partial<WsTestResult>) => {
      if (settled) return;
      settled = true;
      try { ws?.close(); } catch {}
      resolve({
        ok: !!data.ok,
        phase: data.phase || 'unknown',
        error: data.error,
        elapsed_ms: Math.round(performance.now() - started),
        received_connection_established: received,
      });
    };
    try {
      ws = new WebSocket(url);
    } catch (e: any) {
      finish({ ok: false, phase: 'construct', error: e?.message || String(e) });
      return;
    }
    const timer = setTimeout(() => {
      finish({ ok: false, phase: 'timeout', error: 'timeout waiting for open/connection_established' });
    }, timeoutMs);
    ws.onopen = () => {
      console.log('[wsTest] open');
      if (hubId) {
        try {
          const ident = { type: 'identify', hub_id: hubId } as const;
          ws?.send(JSON.stringify(ident));
          console.log('[wsTest] identify sent', ident);
        } catch (e) { console.warn('[wsTest] identify send failed', e); }
      }
      // If server never sends connection_established, we still mark ok after delay
      setTimeout(() => {
        if (!received) {
          finish({ ok: true, phase: 'open-no-message' });
        }
      }, 400);
    };
    ws.onmessage = (ev) => {
      try {
        const j = JSON.parse(ev.data);
        console.log('[wsTest] message', j);
        if (j?.type === 'connection_established') {
          received = true;
          clearTimeout(timer);
          finish({ ok: true, phase: 'connection_established' });
        }
      } catch {
        console.log('[wsTest] message(raw)', ev.data);
      }
    };
    ws.onerror = (e: any) => {
      console.warn('[wsTest] error', e);
      finish({ ok: false, phase: 'error', error: e?.message || String(e) });
    };
    ws.onclose = (ev) => {
      if (!received) {
        finish({ ok: false, phase: 'close', error: `closed code=${ev.code}` });
      }
    };
  });
}
