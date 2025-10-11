// src/pages/PlayerPage.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

/** ---- 設定 ---- */
const WS_BASE =
  import.meta.env.VITE_WS_URL ||
  (location.protocol === "https:" ? "wss://" : "ws://") + location.host;
// 例) VITE_WS_URL=wss://your-server-domain
const SYNC_INTERVAL_MS = 500;

/** ---- 型 ---- */
type WSIn =
  | { type: "ready" }
  | { type: "effect"; action: string }
  | { type: string; [k: string]: any };

type WSOut =
  | { type: "select_video"; video: string }
  | { type: "start_playback" }
  | { type: "sync"; time: number }
  | { type: "end_playback" };

/** ---- 簡易カタログ（必要に応じて差し替え） ---- */
const CATALOG = [
  { title: "デモ映像 1", src: "/assets/movie.mp4", poster: "/assets/poster.jpg" },
  { title: "デモ映像 2", src: "/assets/movie2.mp4" },
];

/** ---- サムネ付きの簡易ピッカー ---- */
function VideoPicker({
  items,
  value,
  onChange,
}: {
  items: { title: string; src: string; poster?: string }[];
  value?: string | null;
  onChange: (src: string) => void;
}) {
  return (
    <div className="grid gap-3 grid-cols-[repeat(auto-fit,minmax(180px,1fr))]">
      {items.map((v) => (
        <button
          key={v.src}
          onClick={() => onChange(v.src)}
          className={`text-left rounded-xl overflow-hidden border ${
            value === v.src ? "border-rose-500 bg-zinc-800" : "border-zinc-700 bg-zinc-900"
          } hover:border-rose-400 transition`}
        >
          <div className="aspect-video bg-black">
            {v.poster ? (
              <img
                src={v.poster}
                alt=""
                className="w-full h-full object-cover select-none pointer-events-none"
                draggable={false}
              />
            ) : null}
          </div>
          <div className="px-3 py-2 text-sm text-white">{v.title}</div>
        </button>
      ))}
    </div>
  );
}

export default function PlayerPage() {
  /** --- セッションID取得 --- */
  const [params] = useSearchParams();
  const sessionId = useMemo(
    () => params.get("session") || sessionStorage.getItem("sessionCode") || "",
    [params]
  );

  /** --- 状態 --- */
  const [selected, setSelected] = useState<string | null>(null); // 選択した動画
  const [deviceReady, setDeviceReady] = useState(false); // デバイス準備OK
  const [wsStatus, setWsStatus] = useState<"idle" | "connecting" | "open" | "closed">("idle");
  const [log, setLog] = useState<string[]>([]);
  const [playing, setPlaying] = useState(false);

  /** --- 参照 --- */
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const syncTimerRef = useRef<number | null>(null);

  /** --- ログ追加 --- */
  const pushLog = (s: string) => {
    setLog((prev) => {
      const next = [s, ...prev];
      return next.length > 50 ? next.slice(0, 50) : next;
    });
    // console側にも出しておく
    console.log(s);
  };

  /** --- WebSocket 接続 --- */
  useEffect(() => {
    if (!sessionId) return;

    setWsStatus("connecting");
    const ws =  new WebSocket("ws://localhost:8000/ws?session=test&role=web")

    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus("open");
      pushLog("✅ WS connected");
    };

    ws.onclose = () => {
      setWsStatus("closed");
      pushLog("❌ WS closed");
    };

    ws.onerror = (e) => {
      pushLog("⚠️ WS error");
    };

    ws.onmessage = (ev) => {
      try {
        const msg: WSIn = JSON.parse(ev.data);
        pushLog(`📩 RECV: ${ev.data}`);

        switch (msg.type) {
          case "ready":
            setDeviceReady(true);
            break;
          case "effect":
            // デバイス側の効果（例：vibrate）をUIに表示したり、何らかの連動があればここで。
            pushLog(`💥 effect: ${msg.action}`);
            break;
          default:
            // 任意のメッセージはログに
            break;
        }
      } catch {
        pushLog("⚠️ invalid WS message");
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId]);

  /** --- WS送信ヘルパ --- */
  const send = (msg: WSOut) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      pushLog("⛔ WS not open");
      return;
    }
    const s = JSON.stringify(msg);
    ws.send(s);
    pushLog(`📤 SEND: ${s}`);
  };

  /** --- 動画選択 → サーバーへ通知（select_video） --- */
  const onSelectVideo = (src: string) => {
    setSelected(src);
    setDeviceReady(false); // 新しい準備を待つ想定
    send({ type: "select_video", video: src });

    // サーバーから {type:"ready"} が来たら deviceReady が true になる
    // デモ用途で”すぐOK”にする場合は↓（本番では不要）
    // setTimeout(() => setDeviceReady(true), 1000);
  };

  /** --- 再生開始 --- */
  const handleStart = async () => {
    if (!selected) return;
    send({ type: "start_playback" });

    try {
      await videoRef.current?.play();
      setPlaying(true);
      startSyncLoop();
    } catch {
      pushLog("⚠️ autoplay blocked");
    }
  };

  /** --- 同期ループ（0.5sごとに currentTime を送る） --- */
  const startSyncLoop = () => {
    stopSyncLoop();
    const tick = () => {
      const t = videoRef.current?.currentTime ?? 0;
      send({ type: "sync", time: Number.isFinite(t) ? t : 0 });
      syncTimerRef.current = window.setTimeout(tick, SYNC_INTERVAL_MS);
    };
    tick();
  };

  const stopSyncLoop = () => {
    if (syncTimerRef.current) {
      window.clearTimeout(syncTimerRef.current);
      syncTimerRef.current = null;
    }
  };

  /** --- 再生終了時 --- */
  const handleEnded = () => {
    setPlaying(false);
    stopSyncLoop();
    send({ type: "end_playback" });
  };

  /** --- 一時停止時（任意。必要なら同期継続してもOK） --- */
  const handlePause = () => {
    setPlaying(false);
    stopSyncLoop();
    // 一時停止をサーバーに送りたいならメッセージを追加してOK
  };

  return (
    <div className="min-h-dvh bg-black text-white p-4">
      <header className="mb-4 flex flex-wrap items-center gap-3">
        <div className="text-sm opacity-80">セッション: <span className="font-mono">{sessionId || "N/A"}</span></div>
        <div className="text-sm opacity-80">WS: {wsStatus}</div>
        <div className="text-sm opacity-80">選択: {selected ? selected.split("/").pop() : "-"}</div>
        <div className={`text-sm ${deviceReady ? "text-green-400" : "text-yellow-300"}`}>
          {deviceReady ? "デバイス準備OK" : "準備待ち…"}
        </div>
      </header>

      {/* 動画選択 */}
      <section className="mb-6">
        <h3 className="mb-2 font-semibold">動画を選択</h3>
        <VideoPicker items={CATALOG} value={selected} onChange={onSelectVideo} />
      </section>

      {/* プレイヤー */}
      <section className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <video
            ref={videoRef}
            src={selected ?? undefined}
            poster={selected ? undefined : "/assets/poster.jpg"}
            className="w-full max-w-[1000px] aspect-video bg-black rounded-xl"
            controls={false}
            playsInline
            preload="auto"
            onEnded={handleEnded}
            onPause={handlePause}
          />
          <div className="mt-3 flex items-center gap-8">
            <button
              onClick={handleStart}
              disabled={!deviceReady || !selected}
              className={`rounded-md px-5 py-2 font-semibold ${
                !deviceReady || !selected
                  ? "bg-zinc-700 text-zinc-400 cursor-not-allowed"
                  : "bg-white text-black hover:bg-zinc-100"
              }`}
            >
              {selected ? (deviceReady ? "▶ 再生開始" : "デバイス準備待ち…") : "動画を選択"}
            </button>
            <button
              onClick={() => videoRef.current?.pause()}
              className="rounded-md px-4 py-2 bg-zinc-800 hover:bg-zinc-700"
            >
              ⏸ 一時停止
            </button>
            <button
              onClick={() => { videoRef.current && (videoRef.current.currentTime = 0); }}
              className="rounded-md px-4 py-2 bg-zinc-800 hover:bg-zinc-700"
            >
              ⏮ 頭出し
            </button>
          </div>
        </div>

        {/* ログパネル */}
        <aside className="bg-zinc-900/70 rounded-xl border border-zinc-800 p-3 h-[300px] overflow-auto">
          <div className="text-sm opacity-80 mb-2">通信ログ</div>
          <ul className="text-xs space-y-1">
            {log.map((l, i) => (
              <li key={i} className="font-mono whitespace-pre-wrap">{l}</li>
            ))}
          </ul>
        </aside>
      </section>
    </div>
  );
}
