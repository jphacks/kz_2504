// src/pages/PlayerPage.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

const FIXED_SESSION_ID = "demo_session";
const WS_SYNC = () =>
  `wss://fourdk-backend-333203798555.asia-northeast1.run.app/api/playback/ws/sync/${encodeURIComponent(FIXED_SESSION_ID)}`;

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

export default function PlayerPage() {
  const { search } = useLocation();
  const q = useMemo(() => new URLSearchParams(search), [search]);

  const contentId = q.get("content");
  const src = useMemo(
    () => (contentId ? `/media/${contentId}.mp4` : "/media/sample.mp4"),
    [contentId]
  );

  const sessionId = useMemo(() => {
    const urlSid = q.get("session");
    if (urlSid) {
      sessionStorage.setItem("sessionId", urlSid);
      return urlSid;
    }
    const stored = sessionStorage.getItem("sessionId");
    if (stored) return stored;
    const temp = `webtest_${Math.random().toString(36).slice(2, 8)}_${Date.now()}`;
    sessionStorage.setItem("sessionId", temp);
    return temp;
  }, [q]);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const progressRef = useRef<HTMLDivElement | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const syncTimerRef = useRef<number | null>(null);
  const lastDragSyncRef = useRef<number>(0);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  const [overlay, setOverlay] = useState<string | null>("読み込み中…");
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

  // ★ 最初の start を「確実に1回だけ」送ったか
  const startSentRef = useRef(false);
  // ★ 再生は始まっているが、まだ送れていない（WS未OPEN/詰まり）の保留フラグ
  const wantStartRef = useRef(false);
  const firstCanPlayDoneRef = useRef(false);

  /* ====== 再生開始（canplayまで待つ） ====== */
  const tryStartPlayback = async () => {
    const v = videoRef.current;
    if (!v) return;
    try {
      v.muted = true;
      setMuted(true);
      await v.play();
      setIsPlaying(true);
      setOverlay(null);
    } catch {
      setOverlay("タップして再生");
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
  const sendStartOnce = async () => {
    if (startSentRef.current) return;
    const v = videoRef.current;
    if (!v || v.paused) return;

    // 送信準備ができるまで待つ（最大3秒）
    const ready = await awaitReady(3000);
    if (!ready) {
      // まだダメ → 少し遅延して再試行（最大3回）
      for (let i = 0; i < 3 && !startSentRef.current; i++) {
        await new Promise((r) => setTimeout(r, 80 * (i + 1)));
        const again = await awaitReady(1000);
        if (again && wsRef.current) {
          try {
            wsRef.current.send(JSON.stringify({ type: "start_continuous_sync" }));
            console.log("WS -> start_continuous_sync (retry#", i + 1, ")");
            startSentRef.current = true;
            wantStartRef.current = false;
            return;
          } catch (_) {}
        }
      }
      // ここまでで送れなければ保留（onopen等で再挑戦）
      wantStartRef.current = true;
      return;
    }

    // 準備OK → 送信
    try {
      wsRef.current?.send(JSON.stringify({ type: "start_continuous_sync" }));
      console.log("WS -> start_continuous_sync");
      startSentRef.current = true;
      wantStartRef.current = false;
    } catch {
      // ごく稀な競合に備え、保留して onopen で再挑戦
      wantStartRef.current = true;
    }
  };

  const unmuteIfPossible = () => {
    const v = videoRef.current; if (!v) return;
    if (v.muted) { v.muted = false; setMuted(false); }
    if (v.volume === 0) v.volume = 1;
  };

  /* ====== WebSocket 接続 ====== */
  const connectWS = () => {
    try {
      const ws = new WebSocket(WS_SYNC());
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setWsError(null);
        reconnectAttemptsRef.current = 0;

        // （要件により定期syncは送らない）

        // OPENになったら、保留があればここで一度だけ送る
        if (wantStartRef.current) {
          // microtaskにずらしてメインスレッドのイベント処理と衝突しにくくする
          Promise.resolve().then(() => { void sendStartOnce(); });
        }
      };

      ws.onmessage = (ev) => {
        try {
          const msg: InMsg = JSON.parse(ev.data);
          if (msg.type === "connection_established") {
            setConnInfo(msg.connection_id);
            console.log("WS connected:", msg);
          } else if (msg.type === "sync_ack") {
            // console.log("sync_ack", msg.received_state, msg.received_time);
          }
        } catch {
          console.log("WS <-", ev.data);
        }
      };

      ws.onerror = () => setWsError("WebSocket error");

      ws.onclose = () => {
        setConnected(false);
        stopSyncLoop(); // 安全
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          setTimeout(connectWS, 1000 * reconnectAttemptsRef.current);
        }
      };
    } catch {
      setWsError("WebSocket connection failed");
    }
  };

  // （未使用）0.5秒周期 sync ループ（コメントアウト維持）
  const startSyncLoop = () => {
    stopSyncLoop();
    syncTimerRef.current = window.setInterval(() => {
      // sendSync();
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
    if (s && s.readyState === WebSocket.OPEN) s.send(JSON.stringify(obj));
  };

  const sendSync = () => {
    const v = videoRef.current;
    const t = seeking ? seekValue : v?.currentTime ?? 0;
    const d = duration || v?.duration || 0;
    const state = computeState();

    const payload: OutMsg = {
      type: "sync",
      state,
      time: t,
      duration: d,
      ts: Date.now(),
    };
    // 定期syncは送らない
    // send(payload);
  };

  useEffect(() => {
    connectWS();
    return () => {
      stopSyncLoop();
      try { wsRef.current?.close(); } catch {}
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  /* ====== video イベント ====== */
  useEffect(() => {
    const v = videoRef.current; if (!v) return;

    const onLoaded = () => {
      setDuration(v.duration || 0);
      setBuffering(v.readyState < 4);
    };

    const onCanPlay = () => {
      setBuffering(false);
      if (!firstCanPlayDoneRef.current) {
        firstCanPlayDoneRef.current = true;
        void tryStartPlayback();
      }
    };

    const onWaiting = () => setBuffering(true);

    const onPlay = () => {
      // 再生要求が出た瞬間（実再生前）に予約
      // 少し遅延させてUI/他イベントと競合しにくくする
      setTimeout(() => { void sendStartOnce(); }, 10);
    };

    const onPlaying = () => {
      setIsPlaying(true);
      setOverlay(null);
      setBuffering(false);
      // 実際に再生が始まったタイミングでも保険で実行（内部で一度きりに抑制）
      setTimeout(() => { void sendStartOnce(); }, 0);
    };

    const onTime   = () => { if (!seeking) setCurrent(v.currentTime || 0); };
    const onPause  = () => { setIsPlaying(false); };
    const onEnded  = () => { setIsPlaying(false); };

    v.addEventListener("loadedmetadata", onLoaded);
    v.addEventListener("canplay", onCanPlay);
    v.addEventListener("waiting", onWaiting);
    v.addEventListener("play", onPlay);       // ★ 追加
    v.addEventListener("playing", onPlaying); // ★ 維持
    v.addEventListener("timeupdate", onTime);
    v.addEventListener("pause", onPause);
    v.addEventListener("ended", onEnded);

    return () => {
      v.removeEventListener("loadedmetadata", onLoaded);
      v.removeEventListener("canplay", onCanPlay);
      v.removeEventListener("waiting", onWaiting);
      v.removeEventListener("play", onPlay);
      v.removeEventListener("playing", onPlaying);
      v.removeEventListener("timeupdate", onTime);
      v.removeEventListener("pause", onPause);
      v.removeEventListener("ended", onEnded);
    };
  }, [seeking]);

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
    if (v.paused) v.play().catch(()=>setOverlay("タップして再生"));
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

  return (
    <>
      <style>{`
        :root{
          --yt-red:#ff0000;
          --hud-gap: clamp(10px, 3vw, 18px);
          --hud-size: clamp(44px, 7vw, 64px);
        }
        .vp{ position:fixed; inset:0; background:#000; color:#fff; font-family: system-ui,-apple-system,Segoe UI,Roboto,"Noto Sans JP",sans-serif; }
        .vp-outer{ position:relative; width:100%; height:100%; overflow:hidden; }
        .vp-video{ position:absolute; inset:0; width:100%; height:100%; object-fit:contain; background:#000; display:block; }

        .vp-loader{ position:absolute; inset:0; display:grid; place-items:center; z-index:6; pointer-events:none; }
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

        .vp-overlay{ position:absolute; inset:0; display:grid; place-items:center; z-index:5; background:rgba(0,0,0,.25); font-weight:700; }
        .vp-note{ margin-top:8px; color:#ffd79a; text-align:center; font-weight:500; }

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
            onLoadedMetadata={(e) => setDuration((e.target as HTMLVideoElement).duration || 0)}
            onTimeUpdate={(e) => { if (!seeking) setCurrent((e.target as HTMLVideoElement).currentTime || 0); }}
            onWaiting={() => setBuffering(true)}
            onPlaying={() => setBuffering(false)}
            onCanPlay={() => setBuffering(false)}
            onError={() => setOverlay("動画の読み込みに失敗しました")}
          />

          {(buffering || overlay) && (
            <div className="vp-loader" aria-hidden="true">
              {overlay ? (
                <div style={{textAlign:"center", lineHeight:1.6}}>
                  <div className="vp-spinner" style={{margin:"0 auto 14px"}} />
                  <div>{overlay}</div>
                  {overlay === "タップして再生" && (
                    <div className="vp-note">ブラウザの自動再生制限によりタップが必要です</div>
                  )}
                </div>
              ) : (
                <div className="vp-spinner" />
              )}
            </div>
          )}

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

          {overlay && (
            <div className="vp-overlay" onClick={() => {
              unmuteIfPossible();
              void tryStartPlayback();
            }}>
              <div>
                <div style={{textAlign:"center"}}>{overlay}</div>
                {overlay === "タップして再生" && (
                  <div className="vp-note">タップで再生を開始します</div>
                )}
              </div>
            </div>
          )}

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
    </>
  );
}
