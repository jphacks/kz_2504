import { BACKEND_API_URL } from "../config/backend";
import type { TimelineEvent, TimelineUploadResponse } from "../types/timeline";

// 入力JSON（任意形）をサーバ仕様の TimelineEvent[] に正規化
function normalizeEvents(rawEvents: any[]): TimelineEvent[] {
  if (!Array.isArray(rawEvents)) return [];
  const out: TimelineEvent[] = [];
  for (const ev of rawEvents) {
    const t = typeof ev?.t === "number" ? ev.t : Number(ev?.time ?? ev?.timestamp ?? NaN);
    // effect/type の解決
    const type: string | undefined =
      typeof ev?.type === "string" ? ev.type :
      typeof ev?.effect === "string" ? ev.effect : undefined;
    if (!isFinite(t) || t < 0 || !type) {
      // caption などはスキップ
      continue;
    }
    // mode の解決（action が mode に混ざっているケースは除外）
    const modeRaw: unknown = ev?.mode ?? ev?.pattern ?? ev?.style;
    const mode = typeof modeRaw === "string" && !/(^start$|^stop$)/i.test(modeRaw) ? modeRaw : undefined;
    const intensity = typeof ev?.intensity === "number" ? ev.intensity : undefined;
    // duration 推定（shot は瞬間系）
    let duration_ms: number | undefined =
      typeof ev?.duration_ms === "number" ? ev.duration_ms :
      typeof ev?.durationMs === "number" ? ev.durationMs : undefined;
    if (!duration_ms && typeof ev?.action === "string" && ev.action.toLowerCase() === "shot") {
      duration_ms = 200; // 短いパルスに寄せる
    }

    out.push({ t, type, mode, intensity, duration_ms });
  }
  return out;
}

export async function sendTimelineToBackend(
  sessionId: string,
  videoId: string,
  timelineJson: { events: TimelineEvent[] }
): Promise<TimelineUploadResponse> {
  if (!timelineJson?.events || timelineJson.events.length === 0) {
    throw new Error("No events in timelineJson");
  }
  // 異形データを正規化
  const events = normalizeEvents(timelineJson.events);
  if (events.length === 0) {
    throw new Error("No valid events after normalization");
  }
  // 開発時は Vite の dev proxy を使うため相対パスを使用する
  const base = import.meta.env.DEV ? "" : BACKEND_API_URL;
  const url = `${base}/api/preparation/upload-timeline/${encodeURIComponent(sessionId)}`;
  const started = performance.now();

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      video_id: videoId,
      timeline_data: { events }
    }),
  });

  const text = await res.text();
  let json: any;
  try { json = JSON.parse(text); } catch {
    throw new Error(`Invalid JSON response (${res.status})`);
  }
  if (!res.ok) {
    const msg = json?.message || json?.error || `HTTP ${res.status}`;
    throw new Error(String(msg));
  }

  const elapsed = Math.round(performance.now() - started);
  // 性能ログ
  console.log("[timeline] uploaded:", {
    elapsed_ms: elapsed,
    size_kb: json?.size_kb,
    events_count: json?.events_count,
    devices_notified: json?.devices_notified,
  });

  return json as TimelineUploadResponse;
}

export async function loadAndSendTimeline(
  sessionId: string,
  videoId: string
): Promise<TimelineUploadResponse> {
  const url = `/json/${encodeURIComponent(videoId)}.json`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Timeline not found: ${videoId}`);
  const timelineJson = await r.json();
  const count = Array.isArray(timelineJson?.events) ? timelineJson.events.length : 0;
  console.log("[timeline] local events(raw):", count);
  const result = await sendTimelineToBackend(sessionId, videoId, timelineJson);
  console.log("[timeline] transmission_time_ms:", result.transmission_time_ms);
  return result;
}

export async function sendTimelineWithRetry(
  sessionId: string,
  videoId: string,
  timelineJson: { events: TimelineEvent[] },
  maxRetries = 3
): Promise<TimelineUploadResponse> {
  let lastErr: unknown = null;
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await sendTimelineToBackend(sessionId, videoId, timelineJson);
    } catch (e) {
      lastErr = e;
      console.error(`[timeline] upload failed (try ${i + 1}/${maxRetries})`, e);
      if (i < maxRetries - 1) {
        const delay = Math.min(1000 * Math.pow(2, i), 5000);
        await new Promise((r) => setTimeout(r, delay));
      }
    }
  }
  throw new Error(`Timeline upload failed after ${maxRetries} retries: ${String((lastErr as Error)?.message || lastErr)}`);
}
