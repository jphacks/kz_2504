import WebSocket from 'ws';
import fs from 'node:fs/promises';
import path from 'node:path';

const DEFAULT_API = 'https://fdx-home-backend-api-47te6uxkwa-an.a.run.app';
const DEFAULT_WS  = 'wss://fdx-home-backend-api-47te6uxkwa-an.a.run.app';

const API_BASE = process.env.VITE_BACKEND_API_URL || DEFAULT_API;
const WS_BASE  = process.env.VITE_BACKEND_WS_URL || DEFAULT_WS;

async function testRestSession() {
  const url = `${API_BASE}/api/v1/session`;
  const payload = { deviceHubId: 'DHX_TEST', videoId: 'sample' };
  const started = Date.now();
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const text = await res.text();
    const ms = Date.now() - started;
    console.log('[REST] POST /api/v1/session ->', res.status, res.statusText, `(${ms}ms)`);
    console.log(text.slice(0, 400));
  } catch (e) {
    console.error('[REST] error:', e);
  }
}

async function testWebSocket() {
  const url = `${WS_BASE}/api/playback/ws/sync/demo_session`;
  console.log('[WS] connecting to', url);
  return new Promise((resolve) => {
    const ws = new WebSocket(url);
    const timer = setTimeout(() => {
      console.error('[WS] timeout (no open within 5s)');
      try { ws.close(); } catch {}
      resolve();
    }, 5000);
    ws.on('open', () => {
      clearTimeout(timer);
      console.log('[WS] open');
      setTimeout(() => { ws.close(); resolve(); }, 1000);
    });
    ws.on('message', (data) => {
      console.log('[WS] message:', String(data).slice(0, 200));
    });
    ws.on('error', (err) => {
      clearTimeout(timer);
      console.error('[WS] error:', err.message || err);
    });
    ws.on('close', (code, reason) => {
      console.log('[WS] close:', code, String(reason));
    });
  });
}

(function(){})
// 正規化（フロント実装と同等）
function normalizeEvents(rawEvents){
  if (!Array.isArray(rawEvents)) return [];
  const out=[];
  for (const ev of rawEvents){
    const t = typeof ev?.t === 'number' ? ev.t : Number(ev?.time ?? ev?.timestamp ?? NaN);
    const type = typeof ev?.type === 'string' ? ev.type : (typeof ev?.effect === 'string' ? ev.effect : undefined);
    if (!Number.isFinite(t) || t < 0 || !type) continue;
    const modeRaw = ev?.mode ?? ev?.pattern ?? ev?.style;
    const mode = (typeof modeRaw === 'string' && !/^start$|^stop$/i.test(modeRaw)) ? modeRaw : undefined;
    let duration_ms = typeof ev?.duration_ms === 'number' ? ev.duration_ms : (typeof ev?.durationMs === 'number' ? ev.durationMs : undefined);
    if (!duration_ms && typeof ev?.action === 'string' && ev.action.toLowerCase() === 'shot') duration_ms = 200;
    const intensity = typeof ev?.intensity === 'number' ? ev.intensity : undefined;
    out.push({ t, type, mode, intensity, duration_ms });
  }
  return out;
}

async function testUploadTimeline(sessionId='demo_session', videoId='demo1'){
  const jsonPath = path.join(process.cwd(), 'public', 'json', `${videoId}.json`);
  const txt = await fs.readFile(jsonPath, 'utf8');
  const raw = JSON.parse(txt);
  const events = normalizeEvents(raw?.events || []);
  console.log('[REST] upload events:', events.length);
  const url = `${API_BASE}/api/preparation/upload-timeline/${encodeURIComponent(sessionId)}`;
  const started = Date.now();
  const res = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_id: videoId, timeline_data: { events } })
  });
  const bodyTxt = await res.text();
  const ms = Date.now()-started;
  console.log('[REST] POST', url, '->', res.status, res.statusText, `(${ms}ms)`);
  console.log(bodyTxt.slice(0, 600));
}

(async () => {
  console.log('API_BASE =', API_BASE);
  console.log('WS_BASE  =', WS_BASE);
  await testRestSession();
  await testWebSocket();
  try { await testUploadTimeline(); } catch(e) { console.error('[upload] error:', e?.message || e); }
})();
