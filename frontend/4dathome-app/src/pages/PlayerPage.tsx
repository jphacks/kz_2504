// src/pages/PlayerPage.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { BACKEND_API_URL, BACKEND_WS_URL } from "../config/backend";
import TimelineUploadButton from "../components/TimelineUploadButton";


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
export default function PlayerPage() {
  const { search } = useLocation();
  const q = useMemo(() => new URLSearchParams(search), [search]);

  const contentId = q.get("content");
  const src = useMemo(
    () => (contentId ? `/video/${contentId}.mp4` : "/video/demo1.mp4"),
    [contentId]
  );

  const [sessionId, setSessionId] = useState<string>("");

  // セッションID初期化
  useEffect(() => {
    // 1. URLクエリから取得
    const urlSid = q.get("session");
    if (urlSid) {
      try { sessionStorage.setItem("sessionId", urlSid); } catch {}
      setSessionId(urlSid);
      return;
    }

    // 2. sessionStorageから取得
    const stored = (() => { try { return sessionStorage.getItem("sessionId"); } catch { return null; } })();
    if (stored) { setSessionId(stored); return; }

    // 3. 環境変数のデフォルト値を使用（READMEに準拠）
    const defaultSid = import.meta.env.VITE_PRODUCTION_SESSION_ID || "demo1";
    try { sessionStorage.setItem("sessionId", defaultSid); } catch {}
    setSessionId(defaultSid);
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

  // 動画準備状態
  const [isVideoReady, setIsVideoReady] = useState(false);

  // タイムラインデータ（エフェクト情報）
  const [timelineEvents, setTimelineEvents] = useState<Array<{t: number; type: string; mode?: string; intensity?: number; duration_ms?: number}>>([]);

  // デバイスハブ接続管理
  const [deviceHubId, setDeviceHubId] = useState("");
  const [isDeviceConnecting, setIsDeviceConnecting] = useState(false); // 接続確認中（WSハンドシェイク待ち）
  const [isDeviceConnected, setIsDeviceConnected] = useState(false);
  const [isTimelineSent, setIsTimelineSent] = useState(false);
  const [timelineUploading, setTimelineUploading] = useState(false); // 再導入: スピナー用
  const [devicesTesting, setDevicesTesting] = useState(false); // デバイステスト待機スピナー
  const [isDevicesTested, setIsDevicesTested] = useState(false);
  const [showPrepareScreen, setShowPrepareScreen] = useState(true);
  const [prepareError, setPrepareError] = useState<string | null>(null);

  // 準備オーバーレイは常にDOMに残し、CSSで非表示化して差し替え時のDOM不整合を防ぐ

  // 全準備完了判定
  const allReady = isDeviceConnected && isVideoReady && isTimelineSent && isDevicesTested;

  // ★ 最初の start を「確実に1回だけ」送ったか
  const startSentRef = useRef(false);
  // ★ 再生は始まっているが、まだ送れていない（WS未OPEN/詰まり）の保留フラグ
  const wantStartRef = useRef(false);
  const firstCanPlayDoneRef = useRef(false);

  /* ====== 再生開始（canplayまで待つ） ====== */
  const tryStartPlayback = async () => {
    // 準備オーバーレイ表示中は再生しない
    if (showPrepareScreen) return;
    const v = videoRef.current;
    if (!v) return;
    try {
      v.muted = true;
      setMuted(true);
      await v.play();
      setIsPlaying(true);
    } catch {
      // 自動再生がブロックされても中央テロップは出さない
    }
  };

  /* ====== 送信を“確実化”するユーティリティ ====== */

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

  /* ====== セッションID 適用 ====== */
  const handleSessionApply = () => {
    const sid = (sessionId || "").trim();
    if (!sid) {
      setPrepareError("セッションIDを入力してください");
      return;
    }
    setPrepareError(null);
    setSessionId(sid);
    try {
      sessionStorage.setItem("sessionId", sid);
    } catch {}
    // URLクエリにも反映（共有しやすくする）
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("session", sid);
      window.history.replaceState({}, "", url.toString());
    } catch {}
  };

  /* ====== デバイスハブ接続処理 ====== */
  const handleDeviceConnect = async () => {
    const hubId = deviceHubId.trim();
    if (!hubId) {
      setPrepareError("デバイスハブIDを入力してください");
      return;
    }
    setPrepareError(null);
    if (isDeviceConnected || isDeviceConnecting) return;
    console.info("[prepare] deviceHubId input accepted", hubId);
    sessionStorage.setItem("deviceHubId", hubId);
    // WebSocket ハンドシェイク確認を開始
    setIsDeviceConnecting(true);
    
    try {
      if (!wsRef.current || wsRef.current.readyState >= WebSocket.CLOSING) {
        connectWS();
      } else {
        // 既にOPENなら message("connection_established")を待つか即判定
        if (connected) {
          // 既に接続確立メッセージを受けているかどうかは connInfo の有無で判定
          if (connInfo) {
            setIsDeviceConnected(true);
            setIsDeviceConnecting(false);
          }
          // 既にOPENなら identify を送って紐付けを明示
          const s = wsRef.current;
          if (s && s.readyState === WebSocket.OPEN) {
            try {
              const msg = { type: "identify", hub_id: hubId };
              s.send(JSON.stringify(msg));
              console.log("[player-ws] identify sent", msg);
            } catch (e) {
              console.warn("[player-ws] identify send failed", e);
            }
          }
        }
      }
      // 新たに handshake 待機をここで実行（レース防止: ws生成後に短い遅延）
      setTimeout(async () => {
        if (isDeviceConnected) return; // すでに完了
        try {
          const ok = await waitWsHandshake(5000);
          if (ok) {
            setIsDeviceConnected(true);
            setPrepareError(null);
          } else {
            setPrepareError("接続確認に失敗しました（タイムアウト）");
          }
        } catch (e: any) {
          setPrepareError(`接続確認中にエラー: ${e?.message || String(e)}`);
        } finally {
          setIsDeviceConnecting(false);
        }
      }, 50);
    } catch (e: any) {
      console.error("[prepare] handleDeviceConnect error", e);
      setPrepareError(`接続エラー: ${e?.message || String(e)}`);
      setIsDeviceConnecting(false);
    }
  };

  /* ====== タイムライン送信（手動） ====== */
  const onTimelineComplete = async () => {
    setIsTimelineSent(true);
    
    // タイムラインJSONを読み込んでイベントデータを保存
    try {
      const videoId = contentId || 'demo1';
      const candidates = [
        `/json/${videoId}.json`,              // 優先: public/json/
        `/sync-data/${videoId}.json`,         // フォールバック
        videoId !== "demo1" ? "/json/demo1.json" : null,
      ].filter(Boolean) as string[];

      for (const url of candidates) {
        try {
          const response = await fetch(url, { cache: "no-cache" });
          if (!response.ok) continue;
          
          const text = await response.text();
          if (/<!DOCTYPE html>/i.test(text) || /<html[\s>]/i.test(text)) continue;
          
          const timelineJson = JSON.parse(text);
          if (timelineJson?.events && Array.isArray(timelineJson.events)) {
            setTimelineEvents(timelineJson.events);
            
            // エフェクトイベントのみカウント
            const effectEvents = timelineJson.events.filter((e: any) => 
              e.action !== "caption" && e.effect
            );
            
            console.log("📋 [タイムライン読込成功]", {
              totalEvents: timelineJson.events.length,
              effectEvents: effectEvents.length,
              captionEvents: timelineJson.events.length - effectEvents.length,
              from: url,
              firstFewEffects: effectEvents.slice(0, 3).map((e: any) => ({
                t: e.t,
                action: e.action,
                effect: e.effect,
                mode: e.mode
              }))
            });
            break;
          }
        } catch (err) {
          console.warn(`タイムラインJSON読み込み失敗: ${url}`, err);
        }
      }
    } catch (e) {
      console.error("❌ タイムラインJSON読み込みエラー", e);
    }
  };
  const onTimelineError = (e: Error) => {
    console.error(e);
    setPrepareError(`タイムライン送信に失敗しました: ${e.message || String(e)}`);
  };

  /* ====== デバイステスト処理（手動） ====== */
  const handleDeviceTest = async () => {
    if (!isTimelineSent) {
      setPrepareError("先にタイムラインを送信してください");
      return;
    }
    setPrepareError(null);

    // デバイステスト（実際はAPIコール）
    setTimeout(() => {
      setIsDevicesTested(true);
    }, 500);
  };

  /* ====== スタートボタン ====== */
  // wsRef を使ってハンドシェイクを待つ（wsTestのロジックをベースにした本番版）
  const waitWsHandshake = (timeoutMs = 5000): Promise<boolean> => {
    return new Promise<boolean>((resolve) => {
      if (connInfo) return resolve(true);
      const ws = wsRef.current;
      if (!ws) {
        // まだ open 前。open 後にフォールバック判定
      }
      let settled = false;
      const done = (ok: boolean) => {
        if (settled) return;
        settled = true;
        try { ws?.removeEventListener("message", onMsg); } catch {}
        try { ws?.removeEventListener("open", onOpen); } catch {}
        try { ws?.removeEventListener("close", onClose); } catch {}
        clearTimeout(timer);
        resolve(ok);
      };
      const onMsg = (ev: MessageEvent) => {
        try {
          const j = JSON.parse((ev as any).data);
          if (j?.type === "connection_established") {
            done(true);
          }
        } catch {}
      };
      const onOpen = () => {
        // サーバが connection_established を送らない場合のフォールバック
        setTimeout(() => {
          if (!settled) done(true);
        }, 400);
      };
      const onClose = () => {
        if (!settled) done(false);
      };
      const timer = setTimeout(() => done(false), timeoutMs);
      wsRef.current?.addEventListener("message", onMsg);
      wsRef.current?.addEventListener("open", onOpen);
      wsRef.current?.addEventListener("close", onClose);
    });
  };

  const handleStartClick = () => {
    if (!allReady) return;
    setShowPrepareScreen(false);
    void tryStartPlayback();
  };

  // ====== 一時的: 接続テストトリガー ======
  const runWsTest = async () => {
    const { runWsHandshakeTest } = await import('../utils/wsTest');
    console.log('[wsTest] starting handshake test…');
    try {
      const result = await runWsHandshakeTest(sessionId, 5000, deviceHubId.trim() || undefined);
      console.log('[wsTest] result', result);
      if (!result.ok) {
        setPrepareError(`WS接続テスト失敗: phase=${result.phase} error=${result.error}`);
      }
    } catch (e: any) {
      setPrepareError(`WS接続テスト例外: ${e?.message || String(e)}`);
    }
  };

  /* ====== 準備フロー補助 ====== */
  // デバイスIDは自動補完のみ（接続はボタンで）- 初回マウント時のみ実行
  const deviceIdInitializedRef = useRef(false);
  useEffect(() => {
    if (!showPrepareScreen) return;
    if (deviceIdInitializedRef.current) return; // 2回目以降はスキップ
    if (deviceHubId) {
      deviceIdInitializedRef.current = true;
      return;
    }
    const hub = q.get("hub") || sessionStorage.getItem("deviceHubId") || "";
    if (hub) {
      setDeviceHubId(hub);
      deviceIdInitializedRef.current = true;
    }
  }, [showPrepareScreen, deviceHubId, q]);

  // デバッグ支援: URLに autoconnect=1 がある場合は自動で接続ボタン相当を1回だけ実行
  const didAutoConnectRef = useRef(false);
  useEffect(() => {
    if (!showPrepareScreen) return;
    if (didAutoConnectRef.current) return;
    const auto = q.get("autoconnect");
    if (auto === "1" && deviceHubId.trim()) {
      didAutoConnectRef.current = true;
      void handleDeviceConnect();
    }
  }, [q, showPrepareScreen, deviceHubId]);


  /* ====== WebSocket 接続 ====== */
  const connectWS = () => {
    try {
      const hubId = deviceHubId.trim();
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
        const hubIdNow = deviceHubId.trim();
        if (hubIdNow && ws.readyState === WebSocket.OPEN) {
          try {
            const msg = { type: "identify", hub_id: hubIdNow };
            ws.send(JSON.stringify(msg));
            console.log("[player-ws] identify sent", msg);
          } catch (e) {
            console.warn("[player-ws] identify send failed", e);
          }
        }
        
        // 接続確認中で、まだ確定していない場合はフォールバックとしてOPENを成功扱い
        setTimeout(() => {
          if (isDeviceConnecting && !isDeviceConnected) {
            console.log("[prepare] WS open fallback -> mark device connected");
            setIsDeviceConnected(true);
            setIsDeviceConnecting(false);
          }
        }, 800);
        
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
            if (isDeviceConnecting && !isDeviceConnected) {
              setIsDeviceConnected(true);
              setIsDeviceConnecting(false);
              console.log("✅ [デバイス接続確認] WebSocketメッセージ受信");
            }
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
        if (!isDeviceConnected) {
          setIsDeviceConnecting(false);
        }
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

  // 0.5秒周期で動画の状態と時間をWebSocketで送信
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
    }, 500);
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

    const onCanPlay = () => {
      setBuffering(false);
      if (!firstCanPlayDoneRef.current) {
        firstCanPlayDoneRef.current = true;
        void tryStartPlayback();
      }
      console.log("[video] canplay");
    };

    const onCanPlayThrough = () => {
      setIsVideoReady(true);
      console.log("[video] canplaythrough ready");
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
    v.addEventListener("canplay", onCanPlay);
    v.addEventListener("canplaythrough", onCanPlayThrough);
    v.addEventListener("waiting", onWaiting);
    v.addEventListener("play", onPlay);
    v.addEventListener("playing", onPlaying);
    v.addEventListener("timeupdate", onTime);
    v.addEventListener("pause", onPause);
    v.addEventListener("ended", onEnded);

    return () => {
      v.removeEventListener("loadedmetadata", onLoaded);
      v.removeEventListener("canplay", onCanPlay);
      v.removeEventListener("canplaythrough", onCanPlayThrough);
      v.removeEventListener("waiting", onWaiting);
      v.removeEventListener("play", onPlay);
      v.removeEventListener("playing", onPlaying);
      v.removeEventListener("timeupdate", onTime);
      v.removeEventListener("pause", onPause);
      v.removeEventListener("ended", onEnded);
    };
  }, [seeking]);

  // 準備オーバーレイが出ている間は常に動画を停止しておく
  useEffect(() => {
    if (showPrepareScreen) {
      try { videoRef.current?.pause(); } catch {}
      setIsPlaying(false);
    }
  }, [showPrepareScreen]);

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
    if (now - lastDragSyncRef.current >= 100) {
      lastDragSyncRef.current = now;
    }
  };

  const onProgressPointerUp = (e: React.PointerEvent) => {
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    setSeeking(false);
    const v = videoRef.current; if (!v) return;
    const t = posToTime(e.clientX);
    v.currentTime = Math.max(0, Math.min(t, v.duration || t));
    setCurrent(v.currentTime);
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

  const togglePlay = () => {
    const v = videoRef.current; if (!v) return;
    unmuteIfPossible();
    if (v.paused) v.play().catch(()=>{});
    else v.pause();
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

  // 準備オーバーレイは動画の上に重ねる（Loginページ風スタイルに合わせる）

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

    /* 準備オーバーレイ */
  .prep-ovr{ position:absolute; inset:0; z-index:7; display:flex; align-items:center; justify-content:center; background:rgba(0,0,0,.35); transition: opacity .18s ease; opacity:1; visibility:visible; pointer-events:auto; }
  .prep-ovr.is-hidden{ opacity:0; visibility:hidden; pointer-events:none; }
        .prep-card{ width:min(560px, 92%); background:rgba(16,20,32,.9); border:1px solid rgba(255,255,255,.12); border-radius:14px; padding:clamp(18px,3.5vw,28px); color:#fff; box-shadow:0 8px 24px rgba(0,0,0,.35); }
        .prep-h1{ font-weight:800; font-size:clamp(18px,3.6vw,22px); margin:0 0 14px; }
        .prep-sec{ padding:12px 0 14px; border-bottom:1px solid rgba(255,255,255,.08); }
        .prep-sec:last-of-type{ border-bottom:none; }
        .prep-label{ font-size:13px; opacity:.9; margin-bottom:6px; }
        /* Loginページに合わせた入力 */
        .xh-input{ width:100%; height:clamp(40px,6.6vw,48px); background:#fff; color:#111; border-radius:6px; border:2px solid #111; padding:0 12px; font-size:clamp(14px,3.2vw,18px); box-shadow:0 2px 0 rgba(0,0,0,.35); }
        .prep-status{ margin-top:8px; font-size:12px; opacity:.95; }
        .prep-status.ok{ color:#79ff7a; }
        .prep-status.err{ color:#ff9f9f; }

        /* Loginページのボタンスタイルに合わせる */
        .xh-btn{ margin-top:14px; min-width:160px; height:clamp(42px,7vw,48px); border:none; border-radius:8px; font-weight:700; cursor:pointer; }
        .xh-btn:disabled{ opacity:.5; cursor:not-allowed; }
        .xh-wide{ width:100%; }
        .xh-login{ background:#fff; color:#111; }
        .xh-debug{ background:#4a90e2; color:#fff; font-size:clamp(13px,2.8vw,15px); }
  /* デバイスハブ 入力＋ボタン行専用調整 */
  .prep-grid{ display:grid; grid-template-columns:1fr auto; gap:10px; align-items:center; }
  .prep-grid .xh-btn{ margin-top:0; }

  /* 汎用: ステータス行スピナー＋チェック */
  .prep-load{ display:flex; align-items:center; gap:12px; }
  .prep-loader{ position:relative; width:30px; height:30px; flex:0 0 30px; }
  .prep-spin{ position:absolute; inset:0; border:3px solid rgba(255,255,255,.25); border-top-color:#fff; border-radius:999px; animation:vp-spin .75s linear infinite; }
  .prep-loader.done .prep-spin{ border:3px solid #79ff7a; animation:none; }
  .prep-check{ position:absolute; inset:0; display:grid; place-items:center; font-size:18px; font-weight:700; color:#79ff7a; text-shadow:0 0 6px rgba(0,0,0,.55); }
  .prep-statusRow{ display:flex; align-items:center; gap:12px; min-height:38px; }
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
            className={`prep-ovr${showPrepareScreen ? "" : " is-hidden"}`}
            aria-hidden={!showPrepareScreen}
          >
            <div className="prep-card">
              <h2 className="prep-h1">再生準備</h2>

              {/* セッションID入力（デバイスハブと同じデザイン） */}
              <div className="prep-sec">
                <div className="prep-label">セッションID</div>
                <div className="prep-grid">
                  <input
                    className="xh-input"
                    placeholder="例: session01"
                    value={sessionId}
                    onChange={(e) => setSessionId(e.target.value)}
                    autoComplete="off"
                  />
                  <button className="xh-btn xh-login" onClick={handleSessionApply}>適用</button>
                </div>
              </div>

              <div className="prep-sec">
                <div className="prep-label">デバイスハブID</div>
                <div className="prep-grid">
                  <input
                    className="xh-input"
                    placeholder="例: DH001"
                    value={deviceHubId}
                    onChange={(e) => setDeviceHubId(e.target.value)}
                    autoComplete="off"
                  />
                  <button className="xh-btn xh-login" onClick={handleDeviceConnect} disabled={isDeviceConnected}>接続</button>
                </div>
              </div>
              <div className="prep-statusRow">
                <div className={`prep-loader ${isDeviceConnected ? 'done' : ''}`}><div className="prep-spin" />{isDeviceConnected && <div className="prep-check">✓</div>}</div>
                <div className={`prep-status ${isDeviceConnected ? 'ok' : ''}`}>
                  {isDeviceConnected ? '接続確認完了' : (isDeviceConnecting ? '接続確認中…' : '未接続')}
                </div>
              </div>

              <div className="prep-sec">
                <div className="prep-label">動画読み込み</div>
                <div className="prep-statusRow" aria-live="polite">
                  <div className={`prep-loader ${isVideoReady ? 'done' : ''}`}><div className="prep-spin" />{isVideoReady && <div className="prep-check">✓</div>}</div>
                  <div className={`prep-status ${isVideoReady ? 'ok' : ''}`}>{isVideoReady ? '読み込み完了' : '読み込み中...'}</div>
                </div>
              </div>

              <div className="prep-sec">
                <div className="prep-label">タイムラインJSON送信</div>
                <div className="prep-statusRow">
                  <div className={`prep-loader ${isTimelineSent ? 'done' : (timelineUploading ? '' : '')}`}><div className="prep-spin" />{isTimelineSent && <div className="prep-check">✓</div>}</div>
                  <div style={{ flex: 1 }}>
                    {isTimelineSent ? (
                      <div className="prep-status ok">送信完了</div>
                    ) : (
                      <TimelineUploadButton
                        sessionId={sessionId}
                        videoId={contentId || 'demo1'}
                        onComplete={() => onTimelineComplete()}
                        onError={onTimelineError}
                        onUploadingChange={(u) => setTimelineUploading(u)}
                        className="xh-btn xh-login"
                      />
                    )}
                  </div>
                </div>
              </div>

              <div className="prep-sec">
                <div className="prep-label">デバイス動作確認</div>
                <div className="prep-statusRow">
                  <div className={`prep-loader ${isDevicesTested ? 'done' : (devicesTesting ? '' : '')}`}><div className="prep-spin" />{isDevicesTested && <div className="prep-check">✓</div>}</div>
                  <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '12px' }}>
                    {isDevicesTested ? (
                      <div className="prep-status ok">確認完了</div>
                    ) : (
                      <button
                        className="xh-btn xh-login"
                        onClick={() => {
                          if (devicesTesting || isDevicesTested || !isTimelineSent) return;
                          setDevicesTesting(true);
                          setTimeout(() => {
                            setDevicesTesting(false);
                            setIsDevicesTested(true);
                          }, 600);
                        }}
                        disabled={!isTimelineSent || devicesTesting || isDevicesTested}
                      >
                        {devicesTesting ? 'テスト中...' : 'テスト実行'}
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {prepareError && <div className="prep-status err">⚠ {prepareError}</div>}

              {/* 明示的に開始ボタン */}
              <div className="prep-sec">
                <div className="prep-label">準備完了後の開始</div>
                <button
                  className="xh-btn xh-login xh-wide"
                  onClick={handleStartClick}
                  disabled={!allReady}
                >
                  再生を開始する
                </button>
                <div style={{ marginTop: 12, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  <button className="xh-btn xh-login" style={{ minWidth: 140 }} onClick={runWsTest}>WS接続テスト</button>
                </div>
              </div>
            </div>
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
              <button className="vp-circle" onClick={togglePlay} aria-label={isPlaying ? "一時停止" : "再生"} title={isPlaying ? "一時停止" : "再生"} disabled={!isVideoReady}>
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


