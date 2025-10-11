// src/pages/PlayerPage.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

const API_BASE = "https://fourdk-backend-333203798555.asia-northeast1.run.app";
const WS_BASE = API_BASE.replace(/^http/i, (m) => (m === "https" ? "wss" : "ws"));

type WSMsg =
  | { type: "start_playback" }
  | { type: "end_playback" }
  | { type: "play" }
  | { type: "pause" }
  | { type: "seek"; time: number }
  | { type: "rate"; rate: number }
  | { type: "sync"; time: number; playing: boolean; seeking?: boolean; buffering?: boolean; progress?: number }
  | { type: "source"; src: string }
  | { type: "effect"; action: string }
  | { type: "ready"; device_ready?: boolean }
  | { type: "error"; message?: string }
  | { [k: string]: any };

export default function PlayerPage() {
  const { search } = useLocation();
  const q = useMemo(() => new URLSearchParams(search), [search]);

  const contentId = q.get("content");
  const src = useMemo(() => (contentId ? `/media/${contentId}.mp4` : "/media/sample.mp4"), [contentId]);

  const urlSession = q.get("session") || "";
  const storageSession = sessionStorage.getItem("sessionId") || sessionStorage.getItem("sessionCode") || "";
  const sessionId = urlSession || storageSession || "";

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const progressRef = useRef<HTMLDivElement | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const syncTimerRef = useRef<number | null>(null);
  const lastDragSyncRef = useRef<number>(0); // ← ドラッグ中の送信間引き

  const [overlay, setOverlay] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [current, setCurrent] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [muted, setMuted] = useState(true);

  const [seeking, setSeeking] = useState(false);
  const [seekValue, setSeekValue] = useState(0);
  const [buffering, setBuffering] = useState(true);

  const [connected, setConnected] = useState(false);
  const [deviceReady, setDeviceReady] = useState<boolean | null>(null);
  const [wsError, setWsError] = useState<string | null>(null);

  /* ---------- 自動再生（初回はミュートで開始） ---------- */
  const tryAutoplay = async () => {
    const v = videoRef.current;
    if (!v) return;
    try {
      v.muted = true;
      await v.play();
      setIsPlaying(true);
      setOverlay(null);
    } catch {
      setOverlay("タップして再生");
    }
  };
  useEffect(() => { tryAutoplay(); /* eslint-disable-next-line */ }, []);
  useEffect(() => { tryAutoplay(); /* eslint-disable-next-line */ }, [src]);

  const unmuteIfPossible = () => {
    const v = videoRef.current; if (!v) return;
    if (v.muted) { v.muted = false; setMuted(false); }
    if (v.volume === 0) v.volume = 1;
  };

  /* ---------- セッション確認（GET） ---------- */
  useEffect(() => {
    let aborted = false;
    (async () => {
      if (!sessionId) return;
      try {
        const res = await fetch(`${API_BASE}/api/sessions/${encodeURIComponent(sessionId)}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json().catch(() => ({}));
        if (!aborted) setDeviceReady(!!data?.device_ready);
      } catch {}
    })();
    return () => { aborted = true; };
  }, [sessionId]);

  /* ---------- WebSocket 接続 ---------- */
  useEffect(() => {
    if (!sessionId) return;
    const url = `${WS_BASE}/ws/sessions/${encodeURIComponent(sessionId)}`;
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setWsError(null);
        sendWS({ type: "join_player", role: "web", session: sessionId });
        if (deviceReady) sendWS({ type: "start_playback" });
      };
      ws.onmessage = (ev) => handleServerMessage(JSON.parse(ev.data));
      ws.onerror   = () => setWsError("WebSocketエラー");
      ws.onclose   = () => setConnected(false);

      return () => { try { ws.close(); } catch {} };
    } catch {
      setWsError("WebSocket接続に失敗しました");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, deviceReady]);

  const sendWS = (message: WSMsg) => {
    const s = wsRef.current;
    if (s && s.readyState === WebSocket.OPEN) s.send(JSON.stringify(message));
  };

  const handleServerMessage = (msg: WSMsg) => {
    const v = videoRef.current; if (!v) return;
    switch (msg.type) {
      case "ready": setDeviceReady(true); break;
      case "play":  unmuteIfPossible(); v.play().catch(() => setOverlay("タップして再生")); break;
      case "pause": v.pause(); break;
      case "seek":
        if (typeof msg.time === "number") {
          v.currentTime = Math.max(0, Math.min(msg.time, v.duration || msg.time));
          setCurrent(v.currentTime);
        }
        break;
      case "sync":
        if (typeof msg.time === "number") {
          const drift = Math.abs((v.currentTime ?? 0) - msg.time);
          if (drift > 0.5) { v.currentTime = msg.time; setCurrent(msg.time); }
        }
        if (typeof msg.playing === "boolean") {
          if (msg.playing && v.paused) v.play().catch(() => setOverlay("タップして再生"));
          if (!msg.playing && !v.paused) v.pause();
        }
        break;
      case "rate":
        if (typeof msg.rate === "number" && msg.rate > 0) v.playbackRate = msg.rate;
        break;
      case "source":
        if (typeof msg.src === "string" && msg.src) {
          v.src = msg.src; v.load(); v.play().catch(() => setOverlay("タップして再生"));
        }
        break;
      case "end_playback":
        v.pause(); v.currentTime = 0; setCurrent(0); setIsPlaying(false); break;
      case "effect":
      case "error":
        break;
    }
  };

  /* ---------- video イベント ---------- */
  useEffect(() => {
    const v = videoRef.current; if (!v) return;
    const onLoaded = () => { setDuration(v.duration || 0); setBuffering(v.readyState < 4); };
    const onCanPlay = () => setBuffering(false);
    const onWaiting = () => setBuffering(true);
    const onPlaying = () => { setIsPlaying(true); setOverlay(null); setBuffering(false); };
    const onTime   = () => { if (!seeking) setCurrent(v.currentTime || 0); };
    const onPause  = () => setIsPlaying(false);
    const onEnded  = () => { setIsPlaying(false); sendWS({ type: "end_playback" }); };

    v.addEventListener("loadedmetadata", onLoaded);
    v.addEventListener("canplay", onCanPlay);
    v.addEventListener("waiting", onWaiting);
    v.addEventListener("playing", onPlaying);
    v.addEventListener("timeupdate", onTime);
    v.addEventListener("pause", onPause);
    v.addEventListener("ended", onEnded);
    return () => {
      v.removeEventListener("loadedmetadata", onLoaded);
      v.removeEventListener("canplay", onCanPlay);
      v.removeEventListener("waiting", onWaiting);
      v.removeEventListener("playing", onPlaying);
      v.removeEventListener("timeupdate", onTime);
      v.removeEventListener("pause", onPause);
      v.removeEventListener("ended", onEnded);
    };
  }, [seeking]);

  /* ---------- 0.5秒ごとのログ＆送信（通常時） ---------- */
  useEffect(() => {
    if (syncTimerRef.current) window.clearInterval(syncTimerRef.current);
    syncTimerRef.current = window.setInterval(() => {
      const v = videoRef.current;
      const displayedTime = seeking ? seekValue : (v?.currentTime ?? 0);
      const playingActive = !!(v && !v.paused && !seeking && !buffering);

      // 例: 12.34,true
      console.log(`${displayedTime.toFixed(2)},${playingActive}`);

      const prog = duration > 0 ? Math.max(0, Math.min(1, displayedTime / duration)) : 0;
      sendWS({ type: "sync", time: displayedTime, playing: playingActive, seeking, buffering, progress: prog });
    }, 500);

    return () => { if (syncTimerRef.current) window.clearInterval(syncTimerRef.current); syncTimerRef.current = null; };
  }, [duration, seeking, seekValue, buffering]);

  /* ---------- 進捗（赤バー & シーク） ---------- */
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
    // 即時ログ＆送信（ドラッグ開始）
    console.log(`${t.toFixed(2)},false`);
    sendWS({ type: "sync", time: t, playing: false, seeking: true, buffering, progress: duration>0 ? t/duration : 0 });
    lastDragSyncRef.current = performance.now();
  };

  const onProgressPointerMove = (e: React.PointerEvent) => {
    if (!seeking) return;
    const t = posToTime(e.clientX);
    setSeekValue(t);

    // ★ ドラッグ中は 100ms 間引きで即時ログ＆送信（iOS等のtimerスロットル対策）
    const now = performance.now();
    if (now - lastDragSyncRef.current >= 100) {
      console.log(`${t.toFixed(2)},false`);
      sendWS({ type: "sync", time: t, playing: false, seeking: true, buffering, progress: duration>0 ? t/duration : 0 });
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
    // 確定時もログ（pausedかどうかはブラウザ状態に従う）
    const playingActive = !!(!v.paused && !buffering);
    console.log(`${v.currentTime.toFixed(2)},${playingActive}`);
    sendWS({ type: "seek", time: v.currentTime });
    sendWS({ type: "sync", time: v.currentTime, playing: playingActive, seeking: false, buffering, progress: duration>0 ? v.currentTime/duration : 0 });
  };

  const onProgressPointerCancel = (e: React.PointerEvent) => {
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    setSeeking(false);
    // キャンセル時も直近値で一度出しておく
    const t = seekValue;
    console.log(`${t.toFixed(2)},false`);
    sendWS({ type: "sync", time: t, playing: false, seeking: false, buffering, progress: duration>0 ? t/duration : 0 });
  };

  /* ---------- 再生/停止 + 5s移動 ---------- */
  const togglePlay = () => {
    const v = videoRef.current; if (!v) return;
    unmuteIfPossible();
    if (v.paused) { v.play().catch(()=>setOverlay("タップして再生")); sendWS({ type: "start_playback" }); }
    else { v.pause(); sendWS({ type: "pause" }); }
  };
  const skip = (sec: number) => {
    const v = videoRef.current; if (!v) return;
    unmuteIfPossible();
    v.currentTime = Math.max(0, Math.min((v.currentTime ?? 0) + sec, v.duration || Infinity));
    // スキップ即時ログ＆送信
    const playingActive = !!(!v.paused && !buffering);
    console.log(`${v.currentTime.toFixed(2)},${playingActive}`);
    sendWS({ type: "seek", time: v.currentTime });
    sendWS({ type: "sync", time: v.currentTime, playing: playingActive, seeking: false, buffering, progress: duration>0 ? v.currentTime/duration : 0 });
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

        .vp-hud{ position:absolute; inset:0; display:grid; grid-template-columns:1fr auto 1fr; align-items:center;
          gap:var(--hud-gap); z-index:3; opacity:0; transition:opacity .18s ease; pointer-events:none; }
        .vp-outer:hover .vp-hud, .vp.touch .vp-hud{ opacity:1; }
        .vp-circle{ width:var(--hud-size); height:var(--hud-size); border-radius:999px; background:rgba(0,0,0,.35);
          border:1px solid rgba(255,255,255,.2); display:grid; place-items:center; pointer-events:auto; cursor:pointer;
          transition: transform .1s ease, background .2s ease, border-color .2s ease; margin-inline:auto; }
        .vp-circle:hover{ transform:translateY(-1px); background:rgba(0,0,0,.45); border-color:rgba(255,255,255,.35); }
        .vp-icon{ width:48%; height:48%; fill:#fff; display:block; }
        .vp-center .vp-circle{ width:calc(var(--hud-size) * 1.1); height:calc(var(--hud-size) * 1.1); }

        .vp-overlay{ position:absolute; inset:0; display:grid; place-items:center; z-index:5; background:rgba(0,0,0,.25); font-weight:700; }
        .vp-note{ margin-top:8px; color:#ffd79a; text-align:center; font-weight:500; }

        .vp-info{ position:absolute; right:10px; bottom:24px; z-index:3; display:flex; flex-direction:column; gap:6px; align-items:flex-end;
          font-feature-settings:"tnum"; font-variant-numeric:tabular-nums; font-size:12px; color:#ddd; opacity:.9; }
        .vp-chip{ background:rgba(0,0,0,.35); padding:4px 6px; border-radius:6px; border:1px solid rgba(255,255,255,.15); }

        @media (hover:none){ .vp{ touch-action: manipulation; } }
      `}</style>

      <div className="vp" onTouchStart={(e)=>{ (e.currentTarget as HTMLDivElement).classList.add("touch"); }}>
        <div className="vp-outer">
          <video
            ref={videoRef}
            className="vp-video"
            src={src}
            playsInline
            muted
            autoPlay
            preload="metadata"
            onClick={togglePlay}
            onLoadedMetadata={(e) => setDuration((e.target as HTMLVideoElement).duration || 0)}
            onTimeUpdate={(e) => { if (!seeking) setCurrent((e.target as HTMLVideoElement).currentTime || 0); }}
            onWaiting={() => setBuffering(true)}
            onPlaying={() => setBuffering(false)}
            onCanPlay={() => setBuffering(false)}
            onError={() => setOverlay("動画の読み込みに失敗しました")}
          />

          {buffering && (
            <div className="vp-loader" aria-hidden="true">
              <div className="vp-spinner" />
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
            <div className="vp-overlay" onClick={togglePlay}>
              <div>
                <div style={{textAlign:"center"}}>{overlay}</div>
                <div className="vp-note">ブラウザの自動再生制限のため、画面をタップしてください</div>
              </div>
            </div>
          )}

          <div className="vp-info">
            <div className="vp-chip">
              {connected ? "WS: connected" : "WS: connecting..."}
              {wsError ? ` / ${wsError}` : ""}
              {deviceReady !== null ? ` / device:${deviceReady ? "ready" : "waiting"}` : ""}
            </div>
            <div className="vp-chip">{fmt(current)} / {fmt(duration)}</div>
          </div>
        </div>
      </div>
    </>
  );
}
