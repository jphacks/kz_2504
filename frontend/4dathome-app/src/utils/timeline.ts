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
  // ベースURLの末尾スラッシュを除去（開発環境でも完全URLを使用）
  const backendBaseUrl = (import.meta.env.VITE_BACKEND_API_URL ?? BACKEND_API_URL ?? "").replace(/\/$/, "");
  const url = `${backendBaseUrl}/api/preparation/upload-timeline/${encodeURIComponent(sessionId)}`;
  const started = performance.now();

  console.log("[timeline] POST start", { url, events: events.length, videoId, sessionId });
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      video_id: videoId,
      timeline_data: { events }
    }),
  });

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const contentType = res.headers.get("content-type") ?? "";
      if (contentType.includes("application/json")) {
        const j = await res.json();
        msg = j?.message || j?.error || msg;
      }
    } catch {}
    console.error("[timeline] POST error", { status: res.status, msg });
    throw new Error(String(msg));
  }

  // 成功時はJSON想定（仕様準拠）。JSONでなければエラーにする。
  const contentType = res.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    console.error("[timeline] POST failed: non-JSON success response");
    throw new Error(`Invalid JSON response (${res.status})`);
  }
  const json: any = await res.json();
  const elapsed = Math.round(performance.now() - started);
  // 性能ログ
  console.log(`✅ JSON送信完了: ${elapsed}ms, ${json?.size_kb}KB, ${json?.events_count}イベント`);
  if (typeof json?.devices_notified === "number") {
    console.log(`   デバイス通知: ${json.devices_notified}台`);
  }

  return json as TimelineUploadResponse;
}

export async function loadAndSendTimeline(
  sessionId: string,
  videoId: string
): Promise<TimelineUploadResponse> {
  // 複数候補パスを試行: /sync-data/{id}.json → /json/{id}.json → /json/demo1.json (フォールバック)
  const candidates = [
    `/sync-data/${encodeURIComponent(videoId)}.json`,
    `/json/${encodeURIComponent(videoId)}.json`,
    videoId !== "demo1" ? "/json/demo1.json" : null,
  ].filter(Boolean) as string[];

  let lastError: Error | null = null;
  let timelineJson: any = null;
  for (const url of candidates) {
    const started = performance.now();
    try {
      console.log("[timeline] fetch local try", { url });
      const r = await fetch(url, { cache: "no-cache" });
      const ct = r.headers.get("content-type") || "";
      const text = await r.text();
      const elapsed = Math.round(performance.now() - started);
      console.log("[timeline] fetch local result", { url, status: r.status, ct, elapsed, snippet: text.slice(0, 60).replace(/\n/g, " ") });
      if (!r.ok) {
        lastError = new Error(`HTTP ${r.status}`);
        continue;
      }
      // index.html などHTMLを誤って受け取ったケースを弾く
      if (/<!DOCTYPE html>/i.test(text) || /<html[\s>]/i.test(text)) {
        lastError = new Error("Received HTML instead of JSON (possible missing file or dev server fallback)");
        continue;
      }
      try {
        timelineJson = JSON.parse(text);
      } catch (e: any) {
        lastError = new Error(`JSON parse error: ${e?.message || String(e)}`);
        continue;
      }
      if (!timelineJson || !Array.isArray(timelineJson.events)) {
        lastError = new Error("Invalid timeline format: missing events array");
        continue;
      }
      // 成功
      const count = timelineJson.events.length;
      console.log("[timeline] local events(raw)", count, { from: url });
      break;
    } catch (e: any) {
      lastError = new Error(e?.message || String(e));
    }
  }

  if (!timelineJson) {
    throw new Error(`Timeline load failed for ${videoId}: ${lastError?.message}`);
  }

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
      const res = await sendTimelineToBackend(sessionId, videoId, timelineJson);
      return res;
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
