import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

const SKIP_SEC = 3;
const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2] as const;
const EPS = 0.04; // 終端シークでの停止回避用の少し手前

export default function PlayerPage() {
  const [params] = useSearchParams();
  const sessionCode = useMemo(
    () => params.get("session") || sessionStorage.getItem("sessionCode") || "N/A",
    [params]
  );

  const vref = useRef<HTMLVideoElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const hideTimer = useRef<number | null>(null);
  const rafId = useRef<number | null>(null);
  const wasPlayingRef = useRef(false); // シーク/ドラッグ前の再生状態を保持
  const lastLogRef = useRef(0);

  const [playing, setPlaying] = useState(false);
  const [rate, setRate] = useState<number>(1);
  const [uiVisible, setUiVisible] = useState(true);
  const [time, setTime] = useState(0);
  const [dur, setDur] = useState(0);
  const [dragTime, setDragTime] = useState<number | null>(null);

  // 表示用フォーマット
  const fmt = (s: number) => {
    if (!isFinite(s)) return "0:00";
    const m = Math.floor(s / 60);
    const ss = Math.floor(s % 60).toString().padStart(2, "0");
    return `${m}:${ss}`;
  };
  const logSeek = (label: string, t: number, d: number) => {
    console.log(`[${label}] ${t.toFixed(2)}s / ${Number.isFinite(d) ? d.toFixed(2) : "--.--"}s`);
  };

  // ===== 再生・操作系 =====
  const togglePlay = async () => {
    const v = vref.current; if (!v) return;
    if (v.paused) { try { await v.play(); setPlaying(true); } catch {} }
    else { v.pause(); setPlaying(false); }
  };

  const skip = async (sec: number) => {
    const v = vref.current; if (!v || !Number.isFinite(v.duration)) return;
    const wasPlaying = !v.paused;
    const target = Math.max(0, Math.min(v.duration - EPS, (v.currentTime || 0) + sec));
    v.currentTime = target;
    setTime(target); // UI即時反映
    logSeek(sec >= 0 ? "SKIP+" + Math.abs(sec) : "SKIP-" + Math.abs(sec), target, v.duration);
    if (wasPlaying) { try { await v.play(); } catch {} }
  };

  const changeSpeed = (s: number) => {
    const v = vref.current; if (!v) return;
    v.playbackRate = s; setRate(s);
  };

  // ===== UI 表示管理 =====
  const showUi = () => {
    setUiVisible(true);
    if (hideTimer.current) window.clearTimeout(hideTimer.current);
    hideTimer.current = window.setTimeout(() => setUiVisible(false), 2500);
  };

  // 初期表示
  useEffect(() => {
    showUi();
    return () => { if (hideTimer.current) window.clearTimeout(hideTimer.current); };
  }, []);

  // コンテナの操作で UI 表示延長
  useEffect(() => {
    const el = containerRef.current; if (!el) return;
    const onInteract = () => showUi();
    el.addEventListener("click", onInteract);
    el.addEventListener("mousemove", onInteract, { passive: true });
    el.addEventListener("touchstart", onInteract, { passive: true });
    return () => {
      el.removeEventListener("click", onInteract);
      el.removeEventListener("mousemove", onInteract);
      el.removeEventListener("touchstart", onInteract);
    };
  }, []);

  // キー操作（Space / ← → / 速度調整）
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!vref.current) return;
      switch (e.key) {
        case " ":
          e.preventDefault(); togglePlay(); showUi(); break;
        case "ArrowRight":
          skip(+SKIP_SEC); showUi(); break;
        case "ArrowLeft":
          skip(-SKIP_SEC); showUi(); break;
        case "[": {
          const i = Math.max(0, SPEEDS.indexOf(rate as any) - 1);
          changeSpeed(SPEEDS[i]); showUi(); break;
        }
        case "]": {
          const i = Math.min(SPEEDS.length - 1, SPEEDS.indexOf(rate as any) + 1);
          changeSpeed(SPEEDS[i]); showUi(); break;
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [rate]);

  // メタデータ取得
  const onLoadedMeta = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    const v = e.currentTarget;
    const d = Number.isFinite(v.duration) ? v.duration : 0;
    setDur(d);
    setTime(v.currentTime || 0);
  };

  // 再生中は rAF で UI を追従（ズレ防止）
  useEffect(() => {
    if (!playing) {
      if (rafId.current) cancelAnimationFrame(rafId.current);
      rafId.current = null;
      return;
    }
    const tick = () => {
      const v = vref.current;
      if (v) setTime(v.currentTime || 0);
      rafId.current = requestAnimationFrame(tick);
    };
    rafId.current = requestAnimationFrame(tick);
    return () => {
      if (rafId.current) cancelAnimationFrame(rafId.current);
      rafId.current = null;
    };
  }, [playing]);

  return (
    <section className="mx-auto max-w-5xl">
      <div ref={containerRef} className="relative overflow-hidden rounded-2xl border border-black/5 bg-black shadow-sm">
        <video
          ref={vref}
          src="/assets/movie.mp4"
          poster="/assets/poster.jpg"
          preload="auto"
          playsInline
          // controls は非表示（カスタムUI）
          onLoadedMetadata={onLoadedMeta}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onTimeUpdate={(e) => {
            // 停止中など rAF が動いていない時の補助更新 & ログ
            const v = e.currentTarget;
            const now = performance.now();
            if (now - lastLogRef.current > 500) {
              logSeek("TIME", v.currentTime, v.duration);
              lastLogRef.current = now;
            }
          }}
          onWaiting={() => console.log("[EVENT] waiting")}
          onCanPlay={() => console.log("[EVENT] canplay")}
          onCanPlayThrough={() => console.log("[EVENT] canplaythrough")}
          className="aspect-video w-full"
        />

        {/* === オーバーレイ === */}
        <div
          className={`pointer-events-none absolute inset-0 transition-opacity duration-200 ${uiVisible ? "opacity-100" : "opacity-0"}`}
          aria-hidden={!uiVisible}
        >
          {/* グラデ */}
          <div className="absolute inset-x-0 top-0 h-20 bg-gradient-to-b from-black/60 to-transparent" />
          <div className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-black/60 to-transparent" />

          {/* 上段：タイトル/セッション */}
          <div className="pointer-events-auto absolute left-0 right-0 top-0 flex items-center justify-between px-4 py-2 text-white">
            <div className="flex items-center gap-2">
              <span className="inline-block h-4 w-1 rounded bg-rose-500" />
              <span className="text-sm font-medium">デモ動画</span>
            </div>
            <span className="rounded bg-white/10 px-2 py-0.5 text-xs">セッション: {sessionCode}</span>
          </div>

          {/* 中央：⏪ / ▶or⏸ / ⏩ */}
          <div className="pointer-events-auto absolute inset-0 flex items-center justify-center">
            <div className="flex items-center gap-6 sm:gap-8">
              <button
                onClick={(e) => { e.stopPropagation(); skip(-SKIP_SEC); showUi(); }}
                disabled={!dur}
                className="rounded-full bg-white/20 p-4 sm:p-5 backdrop-blur hover:bg-white/30 active:scale-[0.98] transition disabled:opacity-40"
                aria-label={`${SKIP_SEC}秒戻る`}
                title={`${SKIP_SEC}秒戻る`}
              >
                <span className="text-3xl text-white">⏪</span>
              </button>

              <button
                onClick={(e) => { e.stopPropagation(); togglePlay(); showUi(); }}
                className="rounded-full bg-white/20 p-4 sm:p-5 backdrop-blur hover:bg-white/30 active:scale-[0.98] transition"
                aria-label={playing ? "一時停止" : "再生"}
                title={playing ? "一時停止" : "再生"}
              >
                <span className="text-3xl text-white">{playing ? "⏸" : "▶"}</span>
              </button>

              <button
                onClick={(e) => { e.stopPropagation(); skip(+SKIP_SEC); showUi(); }}
                disabled={!dur}
                className="rounded-full bg-white/20 p-4 sm:p-5 backdrop-blur hover:bg-white/30 active:scale-[0.98] transition disabled:opacity-40"
                aria-label={`${SKIP_SEC}秒送る`}
                title={`${SKIP_SEC}秒送る`}
              >
                <span className="text-3xl text-white">⏩</span>
              </button>
            </div>
          </div>

          {/* 下段：シーク & 速度 */}
          <div className="pointer-events-auto absolute inset-x-0 bottom-0 px-4 pb-3 text-white">
            <div className="flex items-center gap-3">
              <span className="text-xs tabular-nums">{fmt(dragTime ?? time)}</span>

              <input
                type="range"
                min={0}
                max={dur > 0 ? Math.max(dur - EPS, 0.1) : 1}
                step={0.1}
                value={dragTime ?? Math.min(time, Math.max(dur - EPS, 0))}
                disabled={!dur}
                onPointerDown={() => {
                  showUi();
                  const v = vref.current; if (!v) return;
                  wasPlayingRef.current = !v.paused;
                  v.pause(); setPlaying(false);
                  setDragTime(time);
                }}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setDragTime(val);
                }}
                onPointerUp={async (e) => {
                  const v = vref.current; if (!v) return;
                  const val = Number((e.target as HTMLInputElement).value);
                  const target = Math.max(0, Math.min((v.duration || 0) - EPS, val));
                  v.currentTime = target;
                  setTime(target);
                  setDragTime(null);
                  logSeek("SEEK", target, v.duration);
                  if (wasPlayingRef.current) { try { await v.play(); setPlaying(true); } catch {} }
                  showUi();
                }}
                className="w-full accent-rose-500"
              />

              <span className="text-xs tabular-nums">{fmt(dur)}</span>
            </div>

            <div className="mt-2 flex items-center justify-end gap-2">
              <span className="text-xs">速度</span>
              <select
                value={rate}
                onChange={(e) => { changeSpeed(Number(e.target.value)); showUi(); }}
                className="rounded-md bg-white/10 px-2 py-1 text-sm backdrop-blur"
              >
                {SPEEDS.map((s) => <option key={s} value={s}>{s}x</option>)}
              </select>
            </div>
          </div>
        </div>
        {/* === /オーバーレイ === */}
      </div>

      <p className="mt-3 text-sm text-gray-600">
        画面をタップ/クリックでコントロール表示（2.5秒で自動非表示）。Space/←/→/[/] も使用可。
      </p>
    </section>
  );
}
