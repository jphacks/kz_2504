// src/pages/PlayerPage.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

export default function PlayerPage() {
  const { search } = useLocation();
  const q = useMemo(() => new URLSearchParams(search), [search]);

  // ?content=foo → /media/foo.mp4、無ければ /media/sample.mp4
  const contentId = q.get("content");
  const src = useMemo(
    () => (contentId ? `/media/${contentId}.mp4` : "/media/sample.mp4"),
    [contentId]
  );

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const progressRef = useRef<HTMLDivElement | null>(null);

  const [overlay, setOverlay] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [current, setCurrent] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [muted, setMuted] = useState(true);

  const [seeking, setSeeking] = useState(false);
  const [seekValue, setSeekValue] = useState(0); // 秒（ドラッグ中プレビュー）

  /* ---------- 自動再生（初回はミュートで開始） ---------- */
  const tryAutoplay = async () => {
    const v = videoRef.current;
    if (!v) return;
    try {
      v.muted = true; // モバイル/Chromeでのオートプレイ条件
      await v.play();
      setIsPlaying(true);
      setOverlay(null);
    } catch {
      setOverlay("タップして再生");
    }
  };
  useEffect(() => { tryAutoplay(); }, []);
  useEffect(() => { tryAutoplay(); }, [src]);

  /* ---------- ユーザー操作時に自動アンミュート ---------- */
  const unmuteIfPossible = () => {
    const v = videoRef.current; if (!v) return;
    if (v.muted) { v.muted = false; setMuted(false); }
    if (v.volume === 0) v.volume = 1;
  };

  /* ---------- video イベント ---------- */
  useEffect(() => {
    const v = videoRef.current; if (!v) return;
    const onLoaded = () => setDuration(v.duration || 0);
    const onTime   = () => { if (!seeking) setCurrent(v.currentTime || 0); };
    const onPlay   = () => { setIsPlaying(true); setOverlay(null); };
    const onPause  = () => setIsPlaying(false);

    v.addEventListener("loadedmetadata", onLoaded);
    v.addEventListener("timeupdate", onTime);
    v.addEventListener("play", onPlay);
    v.addEventListener("pause", onPause);
    return () => {
      v.removeEventListener("loadedmetadata", onLoaded);
      v.removeEventListener("timeupdate", onTime);
      v.removeEventListener("play", onPlay);
      v.removeEventListener("pause", onPause);
    };
  }, [seeking]);

  /* ---------- キーボード操作 ---------- */
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const v = videoRef.current; if (!v) return;
      if (["INPUT", "TEXTAREA"].includes((document.activeElement?.tagName ?? ""))) return;
      switch (e.key) {
        case " ":
          e.preventDefault();
          unmuteIfPossible();
          v.paused ? v.play().catch(()=>setOverlay("タップして再生")) : v.pause();
          break;
        case "ArrowRight":
          unmuteIfPossible();
          v.currentTime = Math.min((v.currentTime ?? 0) + 5, v.duration || Infinity);
          break;
        case "ArrowLeft":
          unmuteIfPossible();
          v.currentTime = Math.max((v.currentTime ?? 0) - 5, 0);
          break;
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

  /* ---------- ハンドラ（HUDボタン） ---------- */
  const togglePlay = () => {
    const v = videoRef.current; if (!v) return;
    unmuteIfPossible();
    v.paused ? v.play().catch(()=>setOverlay("タップして再生")) : v.pause();
  };
  const skip = (sec: number) => {
    const v = videoRef.current; if (!v) return;
    unmuteIfPossible();
    v.currentTime = Math.max(0, Math.min((v.currentTime ?? 0) + sec, v.duration || Infinity));
  };

  /* ---------- 進捗（常時表示の赤バー & シーク） ---------- */
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
  };
  const onProgressPointerMove = (e: React.PointerEvent) => {
    if (!seeking) return;
    const t = posToTime(e.clientX);
    setSeekValue(t);
  };
  const onProgressPointerUp = (e: React.PointerEvent) => {
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    setSeeking(false);
    const v = videoRef.current; if (!v) return;
    const t = posToTime(e.clientX);
    v.currentTime = Math.max(0, Math.min(t, v.duration || t));
    setCurrent(v.currentTime);
    unmuteIfPossible(); // シーク確定で音ON
  };
  const onProgressPointerCancel = (e: React.PointerEvent) => {
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    setSeeking(false);
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
          --hud-size: clamp(44px, 7vw, 64px); /* 丸ボタン直径（横に長すぎない） */
        }

        /* 画面いっぱい（トップバー/下ボタンなし） */
        .vp{ position:fixed; inset:0; background:#000; color:#fff; font-family: system-ui,-apple-system,Segoe UI,Roboto,"Noto Sans JP",sans-serif; }
        .vp-outer{ position:relative; width:100%; height:100%; overflow:hidden; }

        /* 動画：比率優先で全画面（トリミングを許すなら contain→cover） */
        .vp-video{ position:absolute; inset:0; width:100%; height:100%; object-fit:contain; background:#000; display:block; }

        /* 赤い進捗バー（常時表示）。ホバー/ドラッグ中は少し太く */
        .vp-progress{
          position:absolute; left:0; right:0; bottom:0; height:14px; /* クリック面積確保 */
          display:block; z-index:4; cursor:pointer;
        }
        .vp-bar{ position:absolute; left:0; right:0; bottom:6px; height:3px; background:rgba(255,255,255,.22); }
        .vp-fill{ position:absolute; left:0; bottom:6px; height:3px; background:var(--yt-red); width:0%; transition:width .06s linear; }
        .vp-outer:hover .vp-bar, .vp-outer:hover .vp-fill,
        .vp-progress.dragging .vp-bar, .vp-progress.dragging .vp-fill{ height:6px; bottom:4px; }

        /* ホバーHUD：左右5s/中央再生。四角いボタンは使わず丸だけ */
        .vp-hud{
          position:absolute; inset:0; display:grid; grid-template-columns:1fr auto 1fr; align-items:center;
          gap:var(--hud-gap); z-index:3; opacity:0; transition:opacity .18s ease;
          pointer-events:none; /* 子要素で有効化 */
        }
        .vp-outer:hover .vp-hud, .vp.touch .vp-hud{ opacity:1; }

        .vp-circle{
          width:var(--hud-size); height:var(--hud-size); border-radius:999px;
          background:rgba(0,0,0,.35); border:1px solid rgba(255,255,255,.2);
          display:grid; place-items:center; pointer-events:auto; cursor:pointer;
          transition: transform .1s ease, background .2s ease, border-color .2s ease;
          margin-inline:auto;
        }
        .vp-circle:hover{ transform:translateY(-1px); background:rgba(0,0,0,.45); border-color:rgba(255,255,255,.35); }
        .vp-icon{ width:48%; height:48%; fill:#fff; display:block; }
        .vp-center .vp-circle{ width:calc(var(--hud-size) * 1.1); height:calc(var(--hud-size) * 1.1); }

        /* オートプレイ案内 */
        .vp-overlay{
          position:absolute; inset:0; display:grid; place-items:center; z-index:5;
          background:rgba(0,0,0,.25); font-weight:700;
        }
        .vp-note{ margin-top:8px; color:#ffd79a; text-align:center; font-weight:500; }

        /* 右下の時間（控えめ・不要なら削除OK） */
        .vp-time{
          position:absolute; right:10px; bottom:24px; z-index:3; font-feature-settings:"tnum"; font-variant-numeric:tabular-nums;
          font-size:12px; color:#ddd; opacity:.85; background:rgba(0,0,0,.35); padding:4px 6px; border-radius:6px;
        }

        @media (hover:none){
          .vp{ touch-action: manipulation; }
        }
      `}</style>

      <div className="vp" onTouchStart={(e)=>{ (e.currentTarget as HTMLDivElement).classList.add("touch"); }}>
        <div className="vp-outer">
          {/* 動画本体 */}
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
            onError={() => setOverlay("動画の読み込みに失敗しました")}
          />

          {/* 進捗バー（クリック/ドラッグでシーク） */}
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

          {/* ホバーHUD（丸アイコンのみ） */}
          <div className="vp-hud" role="group" aria-label="quick controls">
            {/* 左：5s戻し */}
            <div style={{display:"grid", justifyItems:"start", paddingLeft:"min(4vw,24px)"}}>
              <button className="vp-circle" onClick={() => skip(-5)} aria-label="5秒戻す" title="5s戻す">
                <svg className="vp-icon" viewBox="0 0 24 24"><path d="M12 5V2L7 7l5 5V9c3.31 0 6 2.69 6 6 0 .34-.03.67-.08 1h2.02c.04-.33.06-.66.06-1 0-4.42-3.58-8-8-8z"/></svg>
              </button>
            </div>

            {/* 中央：再生/停止 */}
            <div className="vp-center" style={{display:"grid", justifyItems:"center"}}>
              <button className="vp-circle" onClick={togglePlay} aria-label={isPlaying ? "一時停止" : "再生"} title={isPlaying ? "一時停止" : "再生"}>
                {isPlaying
                  ? <svg className="vp-icon" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                  : <svg className="vp-icon" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>}
              </button>
            </div>

            {/* 右：5s進む */}
            <div style={{display:"grid", justifyItems:"end", paddingRight:"min(4vw,24px)"}}>
              <button className="vp-circle" onClick={() => skip(5)} aria-label="5秒進める" title="5s進める">
                <svg className="vp-icon" viewBox="0 0 24 24"><path d="M12 5V2l5 5-5 5V9c-3.31 0-6 2.69-6 6 0 .34.03.67.08 1H4.06C4.02 15.67 4 15.34 4 15c0-4.42 3.58-8 8-8z"/></svg>
              </button>
            </div>
          </div>

          {/* 自動再生制限の案内（初回のみ想定） */}
          {overlay && (
            <div className="vp-overlay" onClick={togglePlay}>
              <div>
                <div style={{textAlign:"center"}}>{overlay}</div>
                <div className="vp-note">ブラウザの自動再生制限のため、画面をタップしてください</div>
              </div>
            </div>
          )}

          {/* 右下の時間表示（控えめ） */}
          <div className="vp-time">{fmt(current)} / {fmt(duration)}</div>
        </div>
      </div>
    </>
  );
}
