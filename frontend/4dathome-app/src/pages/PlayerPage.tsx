// src/pages/PlayerPage.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { BACKEND_API_URL, BACKEND_WS_URL } from "../config/backend";


type SyncState = "play" | "pause" | "seeking" | "seeked";

type InMsg =
  | {
      type: "connection_established";
      connection_id: string;
      session_id: string;
      server_time: string;
      message: string;
    }
  | {
      type: "sync_ack";
      session_id: string;
      received_time: number;
      received_state: SyncState;
      server_time: string;
      relayed_to_devices?: boolean;
    }
  | { type: string; [k: string]: any };

type OutMsg = {
  type: "sync";
  state: SyncState;
  time: number;
  duration: number;
  ts: number;
};

// requestIdleCallback polyfill: commit phase 完了後にstate更新
// 強化版 setState: 同一フレーム内の更新を1回に集約し、commit中タイミングの競合を回避

// 環境変数から同期間隔を取得（ミリ秒）、デフォルトは100ms
const SYNC_INTERVAL_MS = Number(import.meta.env.VITE_SYNC_INTERVAL_MS) || 100;
// シーク中の同期間隔（デフォルトは同期間隔と同じ）
const SEEK_SYNC_INTERVAL_MS = Number(import.meta.env.VITE_SEEK_SYNC_INTERVAL_MS) || SYNC_INTERVAL_MS;

export default function PlayerPage() {
  const { search } = useLocation();
  const q = useMemo(() => new URLSearchParams(search), [search]);

  const contentId = q.get("content");
  const src = useMemo(
    () => (contentId ? `/video/${contentId}.mp4` : "/video/demo1.mp4"),
    [contentId]
  );

  const [sessionId, setSessionId] = useState<string>("");

  // セッションID初期化（URLクエリパラメータから取得）
  useEffect(() => {
    const urlSid = q.get("session");
    if (urlSid) {
      setSessionId(urlSid);
    }
  }, [q]);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const progressRef = useRef<HTMLDivElement | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const syncTimerRef = useRef<number | null>(null);
  const lastDragSyncRef = useRef<number>(0);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  // 中央テロップは使わない方針に変更（スピナーのみ）
  // const [overlay, setOverlay] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [current, setCurrent] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [muted, setMuted] = useState(true);

  const [seeking, setSeeking] = useState(false);
  const [seekValue, setSeekValue] = useState(0);
  const [buffering, setBuffering] = useState(true);

  const [connected, setConnected] = useState(false);
  const [wsError, setWsError] = useState<string | null>(null);
  const [connInfo, setConnInfo] = useState<string | null>(null);

  // タイムラインデータ（エフェクト情報）
  const [timelineEvents, setTimelineEvents] = useState<Array<{t: number; type: string; mode?: string; intensity?: number; duration_ms?: number}>>([]);

  // ★ 最初の start を「確実に1回だけ」送ったか
  const startSentRef = useRef(false);
  // ★ 再生は始まっているが、まだ送れていない（WS未OPEN/詰まり）の保留フラグ
  const wantStartRef = useRef(false);

  /* ====== 送信を"確実化"するユーティリティ ====== */

  // WSがOPEN & バッファが空くまで待機（最大 maxWaitMs）
  const awaitReady = (maxWaitMs = 3000, drainBytes = 64 * 1024): Promise<boolean> => {
    return new Promise((resolve) => {
      const start = performance.now();
      const check = () => {
        const ws = wsRef.current;
        const elapsed = performance.now() - start;
        if (!ws) {
          if (elapsed >= maxWaitMs) return resolve(false);
          return setTimeout(check, 30);
        }
        if (ws.readyState !== WebSocket.OPEN) {
          if (elapsed >= maxWaitMs) return resolve(false);
          return setTimeout(check, 30);
        }
        // backpressure: バッファがある程度捌けるのを待つ
        if (ws.bufferedAmount > drainBytes) {
          if (elapsed >= maxWaitMs) return resolve(false);
          return setTimeout(check, 30);
        }
        resolve(true);
      };
      check();
    });
  };

  // start_continuous_sync を1回だけ確実送信（必要なら数回リトライ）
  // （sendStartOnce 本体は後方に詳細ログ付きで定義）

  const unmuteIfPossible = () => {
    const v = videoRef.current; if (!v) return;
    if (v.muted) { v.muted = false; setMuted(false); }
    if (v.volume === 0) v.volume = 1;
  };

  /* ====== WebSocket 接続 ====== */
  const connectWS = () => {
    try {
      // URLパラメータからdeviceHubIdを取得
      const hubId = q.get("hub")?.trim() || "";
      const url = hubId
        ? `${BACKEND_WS_URL}/api/playback/ws/sync/${encodeURIComponent(sessionId)}?hub=${encodeURIComponent(hubId)}`
        : `${BACKEND_WS_URL}/api/playback/ws/sync/${encodeURIComponent(sessionId)}`;
      console.log("[player-ws] connecting", { url });
      
      // 既存の接続をクリーンアップ
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch (e) {
          console.warn("[player-ws] failed to close existing connection", e);
        }
        wsRef.current = null;
      }
      
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[player-ws] open", { readyState: ws.readyState });
        
        // 状態更新は直接実行（WebSocketイベントなのでReactのcommit phaseとは無関係）
        setConnected(true);
        setWsError(null);
        reconnectAttemptsRef.current = 0;
        
        // ハブIDを明示的にサーバへ通知（任意対応）
        if (hubId && ws.readyState === WebSocket.OPEN) {
          try {
            const msg = { type: "identify", hub_id: hubId };
            ws.send(JSON.stringify(msg));
            console.log("[player-ws] identify sent", msg);
          } catch (e) {
            console.warn("[player-ws] identify send failed", e);
          }
        }
        
        if (wantStartRef.current) {
          setTimeout(() => {
            if (typeof sendStartOnce === 'function') {
              void sendStartOnce();
            }
          }, 0);
        }
      };

      ws.onmessage = (ev) => {
        try {
          const msg: InMsg = JSON.parse(ev.data);
          console.log("📨 [WS受信]", {
            type: msg.type,
            message: msg,
            timestamp: new Date().toISOString()
          });
          if (msg.type === "connection_established") {
            setConnInfo(msg.connection_id);
          }
        } catch {
          console.log("📨 [WS受信(raw)]", ev.data);
        }
      };

      ws.onerror = (e) => {
        console.error("[player-ws] error", e);
        setWsError("WebSocket error");
      };

      ws.onclose = (ev) => {
        console.log("[player-ws] close", { code: ev.code, reason: ev.reason, wasClean: ev.wasClean });
        setConnected(false);
        stopSyncLoop();
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          setTimeout(connectWS, 1000 * reconnectAttemptsRef.current);
        }
      };
    } catch (e) {
      console.error("[player-ws] connect failed", e);
      setWsError("WebSocket connection failed");
    }
  };

  // 任意: ハブIDをWS経由で明示（サーバが理解すれば紐付けされる）。理解しないサーバでも無害。
  const sendIdentify = (hubId: string) => {
    const s = wsRef.current;
    if (!s || s.readyState !== WebSocket.OPEN) return;
    const msg = { type: "identify", hub_id: hubId } as const;
    try {
      s.send(JSON.stringify(msg));
      console.log("📤 [WS送信] identify", {
        message: msg,
        hubId,
        timestamp: new Date().toISOString()
      });
    } catch (e) {
      console.warn("⚠️  [WS送信失敗] identify", e);
    }
  };

  // 現在時刻に該当するアクティブなエフェクトを検索
  // action="start"の場合は次のstopまで有効、action="shot"は瞬間的
  const findActiveEffects = (currentTime: number) => {
    interface ActiveEffect {
      effect: string;
      mode?: string;
      action: string;
      startTime: number;
      endTime: number | null; // nullの場合は動画終了まで
      intensity?: number;
      duration_ms?: number;
    }

    const activeEffects: ActiveEffect[] = [];
    
    // タイムラインをソート（時刻順）
    const sortedEvents = [...timelineEvents].sort((a, b) => a.t - b.t);
    
    // 各effectとmodeの組み合わせごとに、現在アクティブな範囲を追跡
    const activeRanges = new Map<string, { startTime: number; startEvent: any }>();
    
    for (const event of sortedEvents) {
      // captionは除外
      if ((event as any).action === "caption") continue;
      
      const effect = (event as any).effect;
      const mode = (event as any).mode;
      const action = (event as any).action;
      
      if (!effect) continue;
      
      const key = `${effect}_${mode || 'default'}`;
      
      if (action === "start") {
        // 新しい範囲の開始
        activeRanges.set(key, { startTime: event.t, startEvent: event });
      } else if (action === "stop") {
        // 範囲の終了
        const range = activeRanges.get(key);
        if (range && range.startTime <= currentTime && currentTime < event.t) {
          // 現在時刻がこの範囲内にある
          activeEffects.push({
            effect,
            mode,
            action: "start",
            startTime: range.startTime,
            endTime: event.t,
            intensity: (range.startEvent as any).intensity,
            duration_ms: (range.startEvent as any).duration_ms
          });
        }
        activeRanges.delete(key);
      } else if (action === "shot") {
        // shotは瞬間的（±0.1秒）
        if (Math.abs(event.t - currentTime) <= 0.1) {
          activeEffects.push({
            effect,
            mode,
            action: "shot",
            startTime: event.t,
            endTime: event.t,
            intensity: (event as any).intensity,
            duration_ms: (event as any).duration_ms
          });
        }
      }
    }
    
    // まだstopされていない範囲もチェック
    for (const [key, range] of activeRanges.entries()) {
      if (range.startTime <= currentTime) {
        const [effect, modeOrDefault] = key.split('_');
        const mode = modeOrDefault === 'default' ? undefined : modeOrDefault;
        activeEffects.push({
          effect,
          mode,
          action: "start",
          startTime: range.startTime,
          endTime: null, // 終了時刻不明
          intensity: (range.startEvent as any).intensity,
          duration_ms: (range.startEvent as any).duration_ms
        });
      }
    }
    
    return activeEffects;
  };

  // 現在時刻の近くで発生するイベント（start/stop/shot）を検索（ログ表示用）
  const findNearbyEvents = (currentTime: number) => {
    const tolerance = 0.5; // 0.5秒の範囲
    return timelineEvents.filter(event => {
      if ((event as any).action === "caption") return false;
      const t = event.t;
      return t >= currentTime && t < currentTime + tolerance;
    }).map(event => {
      const action = (event as any).action;
      const effect = (event as any).effect;
      const mode = (event as any).mode;
      const t = event.t;
      
      // 次のイベント時刻を探す（stopの場合の範囲表示用）
      let nextT: number | null = null;
      if (action === "start" || action === "stop") {
        const nextEvent = timelineEvents.find(e => 
          e.t > t && 
          (e as any).effect === effect && 
          (e as any).mode === mode &&
          (e as any).action !== "caption"
        );
        if (nextEvent) nextT = nextEvent.t;
      }
      
      return {
        time: t,
        action,
        effect,
        mode,
        nextTime: nextT,
        intensity: (event as any).intensity,
        duration_ms: (event as any).duration_ms
      };
    });
  };

  // 同期ループ: 環境変数で設定された間隔で動画の状態と時間をWebSocketで送信
  const startSyncLoop = () => {
    stopSyncLoop();
    syncTimerRef.current = window.setInterval(() => {
      const v = videoRef.current;
      if (!v || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
      
      const state = computeState();
      const time = v.currentTime || 0;
      const dur = v.duration || 0;
      
      // デバッグ: タイムラインイベント数を確認
      if (Math.floor(time * 2) % 8 === 0) {
        console.log("🔍 [デバッグ]", {
          timelineEventsCount: timelineEvents.length,
          currentTime: time.toFixed(3) + "秒"
        });
      }
      
      // 現在時刻に対応するエフェクトを検索
      const activeEffects = findActiveEffects(time);
      
      const msg: OutMsg = {
        type: "sync",
        state,
        time,
        duration: dur,
        ts: Date.now()
      };
      
      send(msg);
      
      // 近くで発生するイベント（start/stop/shot）をログ出力
      const nearbyEvents = findNearbyEvents(time);
      if (nearbyEvents.length > 0) {
        nearbyEvents.forEach(evt => {
          let rangeStr = "";
          if (evt.action === "start") {
            rangeStr = evt.nextTime !== null 
              ? `${evt.time.toFixed(1)} <= x < ${evt.nextTime.toFixed(1)}`
              : `${evt.time.toFixed(1)} <= x (終了未定)`;
          } else if (evt.action === "stop") {
            rangeStr = `${evt.time.toFixed(1)} <= x < ${(evt.nextTime || (evt.time + 0.5)).toFixed(1)}`;
          } else if (evt.action === "shot") {
            rangeStr = `${evt.time.toFixed(1)} (瞬間)`;
          }
          
          console.log("📍 [イベント発生]", {
            time: evt.time.toFixed(1) + "秒",
            action: evt.action,
            effect: evt.effect,
            mode: evt.mode,
            range: rangeStr,
            intensity: evt.intensity,
            duration_ms: evt.duration_ms
          });
        });
      }
      
      // アクティブなエフェクト一覧（2秒ごと）
      if (Math.floor(time * 2) % 4 === 0 && activeEffects.length > 0) {
        console.log("🎬 [アクティブエフェクト]", {
          currentTime: time.toFixed(3) + "秒",
          activeCount: activeEffects.length,
          effects: activeEffects.map(e => {
            const rangeStr = e.endTime !== null 
              ? `${e.startTime.toFixed(1)} <= x < ${e.endTime.toFixed(1)}`
              : `${e.startTime.toFixed(1)} <= x (終了未定)`;
            return {
              effect: e.effect,
              mode: e.mode,
              action: e.action,
              range: rangeStr,
              intensity: e.intensity,
              duration_ms: e.duration_ms
            };
          }),
          timestamp: new Date().toISOString()
        });
      }
    }, SYNC_INTERVAL_MS);
  };
  const stopSyncLoop = () => {
    if (syncTimerRef.current) {
      clearInterval(syncTimerRef.current);
      syncTimerRef.current = null;
    }
  };

  const computeState = (): SyncState => {
    if (seeking) return "seeking";
    const v = videoRef.current;
    if (!v) return "pause";
    if (v.paused) return "pause";
    if (buffering) return "seeking";
    return "play";
  };

  const send = (obj: OutMsg) => {
    const s = wsRef.current;
    if (s && s.readyState === WebSocket.OPEN) {
      const currentTime = videoRef.current?.currentTime ?? 0;
      // syncメッセージは頻繁なので、2秒ごとにログ表示（それ以外は常に表示）
      const shouldLog = obj.type !== "sync" || Math.floor(currentTime * 2) % 4 === 0;
      if (shouldLog) {
        console.log("📤 [WS送信]", {
          message: obj,
          videoTime: currentTime.toFixed(3) + "秒",
          timestamp: new Date().toISOString()
        });
      }
      s.send(JSON.stringify(obj));
    }
  };

  const sendStartOnce = async () => {
    if (startSentRef.current) return;
    const v = videoRef.current; if (!v || v.paused) return;
    console.log("[player-ws] start_continuous_sync waiting ready");
    const ready = await awaitReady(3000);
    if (!ready) {
      for (let i = 0; i < 3 && !startSentRef.current; i++) {
        await new Promise(r => setTimeout(r, 80 * (i + 1)));
        const again = await awaitReady(1000);
        if (again && wsRef.current) {
          try {
            const msg = { type: "start_continuous_sync" };
            wsRef.current.send(JSON.stringify(msg));
            console.log(`📤 [WS送信] start_continuous_sync retry#${i+1}`, {
              message: msg,
              attempt: i + 1,
              timestamp: new Date().toISOString()
            });
            startSentRef.current = true;
            wantStartRef.current = false;
            return;
          } catch {}
        }
      }
      console.warn("[player-ws] deferred start_continuous_sync (ws not ready)");
      wantStartRef.current = true;
      return;
    }
    try {
      const msg = { type: "start_continuous_sync" };
      wsRef.current?.send(JSON.stringify(msg));
      console.log("📤 [WS送信] start_continuous_sync", {
        message: msg,
        timestamp: new Date().toISOString()
      });
      startSentRef.current = true;
      wantStartRef.current = false;
    } catch {
      console.warn("[player-ws] start_continuous_sync send failed; will retry on open");
      wantStartRef.current = true;
    }
  };

  // 注意: 再生時間の同期はWebSocket経由で行われるため、HTTPポーリングは不要
  // 必要に応じて sync メッセージ（type: "sync"）を WebSocket で送信

  /* ====== video イベント ====== */
  useEffect(() => {
    const v = videoRef.current; if (!v) return;

    const onLoaded = () => {
      setDuration(v.duration || 0);
      setBuffering(v.readyState < 4);
      console.log("[video] loadedmetadata", { duration: v.duration });
    };

    const onWaiting = () => setBuffering(true);

    const onPlay = () => {
      setTimeout(() => {
        if (typeof sendStartOnce === 'function') {
          void sendStartOnce();
        }
      }, 10);
      startSyncLoop(); // 再生開始時に同期ループ開始
      console.log("[video] play - sync loop started");
    };

    const onPlaying = () => {
      setIsPlaying(true);
      setBuffering(false);
      setTimeout(() => {
        if (typeof sendStartOnce === 'function') {
          void sendStartOnce();
        }
      }, 0);
      startSyncLoop(); // 念のため再度開始
      console.log("[video] playing");
    };

    const onTime   = () => { 
      if (!seeking) {
        const currentTime = v.currentTime || 0;
        setCurrent(currentTime);
        
        // 現在時刻の詳細ログ（5秒ごとに表示して負荷軽減）
        if (Math.floor(currentTime) % 5 === 0 && Math.abs(currentTime - Math.floor(currentTime)) < 0.1) {
          console.log("⏱️  [再生時刻]", {
            time: currentTime.toFixed(3) + "秒",
            duration: (v.duration || 0).toFixed(3) + "秒",
            progress: ((currentTime / (v.duration || 1)) * 100).toFixed(1) + "%",
            state: isPlaying ? "再生中" : "一時停止",
            timestamp: new Date().toISOString()
          });
        }
      }
    };
    const onPause  = () => { 
      setIsPlaying(false);
      stopSyncLoop(); // 一時停止時に同期ループ停止
      console.log("[video] pause - sync loop stopped");
    };
    const onEnded  = () => { 
      setIsPlaying(false);
      stopSyncLoop(); // 終了時に同期ループ停止
      console.log("[video] ended - sync loop stopped");
    };

    v.addEventListener("loadedmetadata", onLoaded);
    v.addEventListener("waiting", onWaiting);
    v.addEventListener("play", onPlay);
    v.addEventListener("playing", onPlaying);
    v.addEventListener("timeupdate", onTime);
    v.addEventListener("pause", onPause);
    v.addEventListener("ended", onEnded);

    return () => {
      v.removeEventListener("loadedmetadata", onLoaded);
      v.removeEventListener("waiting", onWaiting);
      v.removeEventListener("play", onPlay);
      v.removeEventListener("playing", onPlaying);
      v.removeEventListener("timeupdate", onTime);
      v.removeEventListener("pause", onPause);
      v.removeEventListener("ended", onEnded);
    };
  }, [seeking]);

  // focus 制御は行わない（従来挙動に戻す）

  /* ====== 進捗（シーク） ====== */
  const pct = duration > 0 ? (seeking ? seekValue / duration : current / duration) : 0;

  const posToTime = (clientX: number) => {
    const el = progressRef.current; if (!el || duration <= 0) return 0;
    const rect = el.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    return ratio * duration;
  };

  const onProgressPointerDown = (e: React.PointerEvent) => {
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    setSeeking(true);
    const t = posToTime(e.clientX);
    setSeekValue(t);
    // 送信はすべて無効化のまま
    lastDragSyncRef.current = performance.now();
  };

  const onProgressPointerMove = (e: React.PointerEvent) => {
    if (!seeking) return;
    const t = posToTime(e.clientX);
    setSeekValue(t);
    const now = performance.now();
    if (now - lastDragSyncRef.current >= SEEK_SYNC_INTERVAL_MS) {
      lastDragSyncRef.current = now;
      // シーク中も環境変数で設定された間隔でWebSocket送信（requestAnimationFrameでReactのコミットフェーズ外で実行）
      requestAnimationFrame(() => {
        const v = videoRef.current;
        if (!v) return;
        const msg: OutMsg = {
          type: "sync",
          state: "seeking",
          time: t,
          duration: v.duration || 0,
          ts: Date.now()
        };
        send(msg);
      });
    }
  };

  const onProgressPointerUp = (e: React.PointerEvent) => {
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    setSeeking(false);
    const v = videoRef.current; if (!v) return;
    const t = posToTime(e.clientX);
    v.currentTime = Math.max(0, Math.min(t, v.duration || t));
    setCurrent(v.currentTime);
    
    // シーク完了をWebSocketで送信
    requestAnimationFrame(() => {
      const msg: OutMsg = {
        type: "sync",
        state: "seeked",
        time: v.currentTime,
        duration: v.duration || 0,
        ts: Date.now()
      };
      send(msg);
    });
    
    unmuteIfPossible();
  };

  const onProgressPointerCancel = (e: React.PointerEvent) => {
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    setSeeking(false);
  };

  /* ====== キーボード/ボタン ====== */
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const v = videoRef.current; if (!v) return;
      if (["INPUT", "TEXTAREA"].includes((document.activeElement?.tagName ?? ""))) return;
      switch (e.key) {
        case " ":
          e.preventDefault(); togglePlay(); break;
        case "ArrowRight":
          skip(5); break;
        case "ArrowLeft":
          skip(-5); break;
        case "m": case "M":
          v.muted = !v.muted; setMuted(v.muted); break;
        case "f": case "F":
          if (document.fullscreenElement) document.exitFullscreen();
          else v.parentElement?.requestFullscreen();
          break;
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  /* ====== 再生開始処理（handlePlay） ====== */
  const handlePlay = () => {
    const v = videoRef.current;
    if (!v) {
      console.warn("❌ [handlePlay] video element not found");
      return;
    }

    console.log("▶️  [handlePlay] 再生開始処理開始");
    
    // 1. 状態更新
    setIsPlaying(true);
    
    // 2. 既存の送信インターバルをクリア（重複防止）
    stopSyncLoop();
    console.log("   既存の同期ループをクリア");
    
    // 3. WebSocket接続状態を確認
    const ws = wsRef.current;
    const wsReady = ws && ws.readyState === WebSocket.OPEN;
    const hubId = q.get("hub")?.trim() || "";
    console.log("   WebSocket状態:", {
      connected: wsReady,
      readyState: ws?.readyState,
      sessionId,
      hubId
    });
    
    // 4. HTML5動画を再生
    v.play()
      .then(() => {
        console.log("✅ [handlePlay] 動画再生成功");
        
        // 5. 500ms間隔の同期ループを開始
        startSyncLoop();
        console.log("   同期ループ開始（間隔: " + SYNC_INTERVAL_MS + "ms）");
        
        // 6. 初回同期メッセージを即座に送信
        if (wsReady) {
          const currentTime = v.currentTime || 0;
          const msg: OutMsg = {
            type: "sync",
            state: "play",
            time: currentTime,
            duration: v.duration || 0,
            ts: Date.now()
          };
          send(msg);
          console.log("📤 [handlePlay] 初回同期メッセージ送信", {
            time: currentTime.toFixed(3) + "秒",
            state: "play"
          });
        } else {
          console.warn("⚠️  [handlePlay] WebSocket未接続のため同期メッセージ送信不可");
        }
      })
      .catch((err) => {
        console.error("❌ [handlePlay] 動画再生失敗", err);
        setIsPlaying(false);
      });
  };

  /* ====== 一時停止処理（handlePause） ====== */
  const handlePause = () => {
    const v = videoRef.current;
    if (!v) {
      console.warn("❌ [handlePause] video element not found");
      return;
    }

    console.log("⏸️  [handlePause] 一時停止処理開始");
    
    // 1. 動画を一時停止
    v.pause();
    
    // 2. 状態更新
    setIsPlaying(false);
    
    // 3. 同期ループを停止
    stopSyncLoop();
    console.log("   同期ループ停止");
    
    // 4. 一時停止メッセージを送信
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      const msg: OutMsg = {
        type: "sync",
        state: "pause",
        time: v.currentTime || 0,
        duration: v.duration || 0,
        ts: Date.now()
      };
      send(msg);
      console.log("📤 [handlePause] 一時停止メッセージ送信");
    } else {
      console.warn("⚠️  [handlePause] WebSocket未接続のため送信スキップ");
    }
  };

  const togglePlay = () => {
    const v = videoRef.current; if (!v) return;
    unmuteIfPossible();
    if (v.paused) {
      handlePlay(); // 明示的なhandlePlayを使用
    } else {
      handlePause(); // 明示的なhandlePauseを使用
    }
  };

  const skip = (sec: number) => {
    const v = videoRef.current; if (!v) return;
    unmuteIfPossible();
    v.currentTime = Math.max(0, Math.min((v.currentTime ?? 0) + sec, v.duration || Infinity));
  };

  const fmt = (t: number) => {
    if (!isFinite(t) || t < 0) t = 0;
    const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = Math.floor(t % 60);
    return h > 0 ? `${h}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}` : `${m}:${String(s).padStart(2,"0")}`;
  };

  /* ====== WebSocket 初期化 ====== */
  useEffect(() => {
    if (!sessionId) return;
    console.log("[player-ws] initializing connection", { sessionId });
    connectWS();
  }, [sessionId]);

  /* ====== WebSocket クリーンアップ ====== */
  useEffect(() => {
    // コンポーネントアンマウント時にWebSocket接続をクリーンアップ
    return () => {
      console.log("[player-ws] cleanup on unmount");
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch (e) {
          console.warn("[player-ws] cleanup close error", e);
        }
        wsRef.current = null;
      }
      stopSyncLoop();
    };
  }, []);

  return (
    <div className="vp-root-wrapper">
      <style>{`
        :root{
          --yt-red:#ff0000;
          --hud-gap: clamp(10px, 3vw, 18px);
          --hud-size: clamp(44px, 7vw, 64px);
        }
        .vp{ position:fixed; inset:0; background:#000; color:#fff; font-family: system-ui,-apple-system,Segoe UI,Roboto,"Noto Sans JP",sans-serif; }
        .vp-outer{ position:relative; width:100%; height:100%; overflow:hidden; }
        .vp-video{ position:absolute; inset:0; width:100%; height:100%; object-fit:contain; background:#000; display:block; }

        .vp-loader{ position:absolute; inset:0; display:grid; place-items:center; z-index:6; pointer-events:none; transition: opacity .18s ease; }
        .is-hidden{ opacity:0 !important; pointer-events:none !important; visibility:hidden !important; }
        .vp-spinner{ width:42px; height:42px; border:3px solid rgba(255,255,255,.28); border-top-color:#fff; border-radius:999px; animation:vp-spin .8s linear infinite; }
        @keyframes vp-spin { to { transform: rotate(360deg); } }

        .vp-progress{ position:absolute; left:0; right:0; bottom:0; height:14px; display:block; z-index:4; cursor:pointer; }
        .vp-bar{ position:absolute; left:0; right:0; bottom:6px; height:3px; background:rgba(255,255,255,.22); }
        .vp-fill{ position:absolute; left:0; bottom:6px; height:3px; background:var(--yt-red); width:0%; transition:width .06s linear; }
        .vp-outer:hover .vp-bar, .vp-outer:hover .vp-fill,
        .vp-progress.dragging .vp-bar, .vp-progress.dragging .vp-fill{ height:6px; bottom:4px; }

        .vp-hud{ position:absolute; inset:0; display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:var(--hud-gap); z-index:3; opacity:0; transition:opacity .18s ease; pointer-events:none; }
        .vp-outer:hover .vp-hud, .vp.touch .vp-hud{ opacity:1; }
        .vp-circle{ width:var(--hud-size); height:var(--hud-size); border-radius:999px; background:rgba(0,0,0,.35);
          border:1px solid rgba(255,255,255,.2); display:grid; place-items:center; pointer-events:auto; cursor:pointer;
          transition: transform .1s ease, background .2s ease, border-color .2s ease; margin-inline:auto; }
        .vp-circle:hover{ transform:translateY(-1px); background:rgba(0,0,0,.45); border-color:rgba(255,255,255,.35); }
        .vp-icon{ width:48%; height:48%; fill:#fff; display:block; }

  /* 中央テロップは廃止 */

        .vp-info{ position:absolute; right:10px; bottom:24px; z-index:3; display:flex; flex-direction:column; gap:6px; align-items:flex-end;
          font-feature-settings:"tnum"; font-variant-numeric:tabular-nums; font-size:12px; color:#ddd; opacity:.9; }
        .vp-chip{ background:rgba(0,0,0,.35); padding:4px 6px; border-radius:6px; border:1px solid rgba(255,255,255,.15); }
      `}</style>

      <div className="vp" onTouchStart={(e)=>{ (e.currentTarget as HTMLDivElement).classList.add("touch"); }}>
        <div className="vp-outer">
          <video
            ref={videoRef}
            className="vp-video"
            src={src}
            playsInline
            preload="auto"
            muted
            onClick={togglePlay}
            onLoadedMetadata={(e) => { const d = (e.target as HTMLVideoElement).duration || 0; setDuration(d); }}
            onTimeUpdate={(e) => { if (!seeking) { const t = (e.target as HTMLVideoElement).currentTime || 0; setCurrent(t); } }}
            onWaiting={() => setBuffering(true)}
            onPlaying={() => setBuffering(false)}
            onCanPlay={() => setBuffering(false)}
            onError={() => { /* 中央テロップは出さない */ }}
          />

          <div className={`vp-loader${buffering ? '' : ' is-hidden'}`} aria-hidden="true">
            <div className="vp-spinner" />
          </div>

          <div
            ref={progressRef}
            className={`vp-progress${seeking ? " dragging" : ""}`}
            onPointerDown={onProgressPointerDown}
            onPointerMove={onProgressPointerMove}
            onPointerUp={onProgressPointerUp}
            onPointerCancel={onProgressPointerCancel}
          >
            <div className="vp-bar" />
            <div className="vp-fill" style={{ width: `${Math.max(0, Math.min(1, pct)) * 100}%` }} />
          </div>

          <div className="vp-hud" role="group" aria-label="quick controls">
            <div style={{display:"grid", justifyItems:"start", paddingLeft:"min(4vw,24px)"}}>
              <button className="vp-circle" onClick={() => skip(-5)} aria-label="5秒戻す" title="5s戻す">
                <svg className="vp-icon" viewBox="0 0 24 24"><path d="M12 5V2L7 7l5 5V9c3.31 0 6 2.69 6 6 0 .34-.03.67-.08 1h2.02c.04-.33.06-.66.06-1 0-4.42-3.58-8-8-8z"/></svg>
              </button>
            </div>
            <div className="vp-center" style={{display:"grid", justifyItems:"center"}}>
              <button className="vp-circle" onClick={togglePlay} aria-label={isPlaying ? "一時停止" : "再生"} title={isPlaying ? "一時停止" : "再生"}>
                {isPlaying
                  ? <svg className="vp-icon" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                  : <svg className="vp-icon" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>}
              </button>
            </div>
            <div style={{display:"grid", justifyItems:"end", paddingRight:"min(4vw,24px)"}}>
              <button className="vp-circle" onClick={() => skip(5)} aria-label="5秒進める" title="5s進める">
                <svg className="vp-icon" viewBox="0 0 24 24"><path d="M12 5V2l5 5-5 5V9c-3.31 0-6 2.69-6 6 0 .34.03.67.08 1H4.06C4.02 15.67 4 15.34 4 15c0-4.42 3.58-8 8-8z"/></svg>
              </button>
            </div>
          </div>

          <div className="vp-info">
            <div className="vp-chip">
              {connected ? "WS: connected" : "WS: connecting..."}
              {wsError ? ` / ${wsError}` : ""}
              {connInfo ? ` / id:${connInfo}` : ""}
              {sessionId ? ` / session:${sessionId}` : ""}
            </div>
            <div className="vp-chip">{fmt(current)} / {fmt(duration)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}


