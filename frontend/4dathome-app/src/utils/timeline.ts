import { BACKEND_API_URL } from "../config/backend";
import type { TimelineEvent, TimelineUploadResponse } from "../types/timeline";

export async function sendTimelineToBackend(
  sessionId: string,
  videoId: string,
  timelineJson: { events: any[] }
): Promise<TimelineUploadResponse> {
  if (!timelineJson?.events || timelineJson.events.length === 0) {
    throw new Error("No events in timelineJson");
  }
  
  // JSONをそのまま送信（正規化なし）
  const events = timelineJson.events;
  console.log("📦 [timeline] イベントデータ準備完了（正規化なし）");
  console.log("   イベント数:", events.length);
  
  // ベースURLの末尾スラッシュを除去（開発環境でも完全URLを使用）
  const backendBaseUrl = (import.meta.env.VITE_BACKEND_API_URL ?? BACKEND_API_URL ?? "").replace(/\/$/, "");
  const url = `${backendBaseUrl}/api/preparation/upload-timeline/${encodeURIComponent(sessionId)}`;
  const started = performance.now();

  const payload = {
    video_id: videoId,
    timeline_data: { events }
  };
  
  console.log("📤 [timeline] 送信するJSONデータ:");
  console.log(JSON.stringify(payload, null, 2));

  console.log("[timeline] POST start", { url, events: events.length, videoId, sessionId });
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
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
  // 選択した動画のvideoIdと同じ名前のJSONファイルのみを読み込む（フォールバックなし）
  const url = `/json/${encodeURIComponent(videoId)}.json`;

  console.log("📤 [timeline] 送信開始 ============");
  console.log("   Session ID:", sessionId);
  console.log("   Video ID:", videoId);
  console.log("   読み込むファイル:", url);

  let timelineJson: any = null;
  const started = performance.now();
  
  try {
    console.log("[timeline] fetch local try", { url, videoId });
    const r = await fetch(url, { cache: "no-cache" });
    const ct = r.headers.get("content-type") || "";
    const text = await r.text();
    const elapsed = Math.round(performance.now() - started);
    console.log("[timeline] fetch local result", { url, status: r.status, ct, elapsed, snippet: text.slice(0, 60).replace(/\n/g, " ") });
    
    if (!r.ok) {
      throw new Error(`JSONファイルが見つかりません: ${url} (HTTP ${r.status})`);
    }
    
    // index.html などHTMLを誤って受け取ったケースを弾く
    if (/<!DOCTYPE html>/i.test(text) || /<html[\s>]/i.test(text)) {
      throw new Error(`JSONファイルの代わりにHTMLが返されました: ${url} (ファイルが存在しない可能性があります)`);
    }
    
    try {
      timelineJson = JSON.parse(text);
    } catch (e: any) {
      throw new Error(`JSON parse error: ${e?.message || String(e)}`);
    }
    
    if (!timelineJson || !Array.isArray(timelineJson.events)) {
      throw new Error(`Invalid timeline format: missing events array in ${url}`);
    }
    
    // 成功
    const count = timelineJson.events.length;
    console.log("✅ [timeline] JSONファイル読み込み成功");
    console.log("   ファイル:", url);
    console.log("   イベント数(raw):", count);
    console.log("   最初の3イベント:", timelineJson.events.slice(0, 3));
  } catch (e: any) {
    console.error("❌ [timeline] JSONファイル読み込み失敗");
    console.error("   ファイル:", url);
    console.error("   エラー:", e.message);
    throw new Error(`タイムライン読み込み失敗 (${videoId}.json): ${e?.message || String(e)}`);
  }

  console.log("📨 [timeline] バックエンドへ送信開始...");
  const result = await sendTimelineToBackend(sessionId, videoId, timelineJson);
  console.log("✅ [timeline] 送信完了 ============");
  console.log("   送信時間:", result.transmission_time_ms, "ms");
  console.log("   イベント数:", result.events_count);
  console.log("   データサイズ:", result.size_kb, "KB");
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
