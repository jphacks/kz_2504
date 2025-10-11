import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

/** Pairing：背景フル / ヘッダーは左=長方形ロゴ（幅は高さ×2）・右=丸アイコン2つ */
export default function PairingPage() {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [deviceReady, setDeviceReady] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const c = code.trim();
    if (!c) return setError("コードを入力してください");
    setError(null); setLoading(true); setDeviceReady(false);
    try {
      const res = await fetch(`https://your-server-domain/api/sessions/${c}`);
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      sessionStorage.setItem("sessionCode", c);
      connectWebSocket(c);
      if (data?.device_ready) setDeviceReady(true);
    } catch {
      setError("セッションが無効か、サーバーに接続できません");
      setLoading(false);
    }
  };

  const connectWebSocket = (sessionId: string) => {
    try {
      const ws = new WebSocket(`wss://your-server-domain/ws/sessions/${sessionId}`);
      wsRef.current = ws;
      ws.onopen = () => setLoading(false);
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data);
        if (msg.type === "ready") setDeviceReady(true);
        if (msg.type === "error") setError(msg.message || "サーバーエラー");
      };
    } catch {
      setError("WebSocket接続に失敗しました"); setLoading(false);
    }
  };

  const handleStart = () => {
    const sessionCode = code.trim();
    if (!sessionCode) return;
    wsRef.current?.send(JSON.stringify({ type: "start_playback" }));
    sessionStorage.setItem("sessionCode", sessionCode);
    navigate(`/player?session=${encodeURIComponent(sessionCode)}`);
  };

  useEffect(() => () => wsRef.current?.close(), []);

  return (
    <>
      <style>{`
        :root{
          --xh-h: clamp(52px, 7vw, 64px);
          --pad: clamp(12px, 3vw, 18px);
          --ico: clamp(28px, 5vw, 34px);
          --gap: clamp(10px, 2.4vw, 16px);
          --logo-h: clamp(32px, 5vw, 44px);
          --logo-w-base: calc(var(--logo-h) * 2); /* 幅=高さ×2（長方形） */
          --logo-w: max(80px, min(
            var(--logo-w-base),
            calc(100vw - (var(--pad) * 2) - (var(--ico) * 2) - var(--gap) - 12px)
          ));
        }

        .xh-root{ position: fixed; inset:0; color:#fff; }
        .xh-bg{ position:absolute; inset:0; background:url('/PairingPage.jpeg') center/cover no-repeat fixed; }
        .xh-shade{ position:absolute; inset:0; background: radial-gradient(80% 70% at 50% 30%, transparent 0%, rgba(0,0,0,.35) 60%, rgba(0,0,0,.55) 100%); }

        /* 固定ヘッダー（Gridで左右固定/中央スペーサ） */
        .xh-top{
          position:fixed; inset:0 0 auto 0; height:var(--xh-h);
          background:#000; border-bottom:1px solid rgba(255,255,255,.1);
          padding:0 var(--pad); z-index:20;
          display:grid; grid-template-columns:auto 1fr auto; align-items:center; column-gap:12px;
        }
        .xh-left{ min-width:0; display:flex; align-items:center; }
        .xh-right{ display:flex; align-items:center; gap:var(--gap); }

        .xh-logoBox{ width:var(--logo-w); height:var(--logo-h); border-radius:8px;
          overflow:hidden; border:1px solid rgba(255,255,255,.12);
          display:grid; place-items:center; background:transparent; }
        .xh-logoImg{ width:100%; height:100%; object-fit:contain; display:block; }

        .xh-ico{ width:var(--ico); height:var(--ico); border-radius:999px; background:#e9e9e9;
          display:grid; place-items:center; box-shadow:0 1px 0 rgba(0,0,0,.5) inset; }
        .xh-ico img{ width:60%; height:60%; object-fit:contain; display:block; filter:saturate(0); }

        .xh-content-pad{ padding-top: var(--xh-h); }

        /* 本文 */
        .xh-main{ position:relative; min-height:100vh; display:grid; grid-template-rows:var(--xh-h) 1fr; }
        .xh-center{ display:flex; align-items:center; justify-content:center; padding: clamp(12px,4vw,24px); text-align:center; }
        .xh-title{ margin:0 0 10px; font-weight:800; font-size:clamp(18px,3.6vw,28px); text-shadow:0 1px 2px rgba(0,0,0,.35); }
        .xh-field{ width:min(80vw,420px); display:inline-block; }
        .xh-input{ width:100%; height:clamp(40px,6.6vw,48px); background:#fff; color:#111; border-radius:6px; border:2px solid #111; padding:0 12px; font-size:clamp(14px,3.2vw,18px); box-shadow:0 2px 0 rgba(0,0,0,.35); }
        .xh-btn{ margin-top:14px; min-width:160px; height:clamp(42px,7vw,48px); border:none; border-radius:8px; font-weight:700; cursor:pointer; }
        .xh-connect{ background:#fff; color:#111; }
        .xh-ready{ margin-top:16px; color:#b7f7c5; }
        .xh-start{ margin-top:10px; background:#34d399; color:#111; }
        .xh-err{ margin-top:8px; color:#ffe08a; }
      `}</style>

      <div className="xh-root" aria-live="polite">
        <div className="xh-bg" aria-hidden="true" />
        <div className="xh-shade" aria-hidden="true" />

        <header className="xh-top" role="banner">
          <div className="xh-left">
            <div className="xh-logoBox" title="Home">
              <img src="/logg.jpeg" alt="Logo" className="xh-logoImg"
                   onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
            </div>
          </div>
          <div aria-hidden="true" />
          <div className="xh-right">
            <div className="xh-ico" title="System">
              <img src="/system.jpeg" alt="" onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
            </div>
            <div className="xh-ico" title="Notifications">
              <img src="/bell.jpeg" alt="" onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
            </div>
          </div>
        </header>

        <main className="xh-main xh-content-pad">
          <div />
          <div className="xh-center">
            <form onSubmit={handleSubmit} aria-labelledby="pairingTitle">
              <h1 id="pairingTitle" className="xh-title">デバイスのIDを入力してください</h1>
              <div className="xh-field">
                <input className="xh-input" value={code} onChange={(e)=>setCode(e.target.value)}
                       placeholder="デバイスID" inputMode="text" autoComplete="one-time-code" />
              </div>

              {error && <div className="xh-err">⚠ {error}</div>}

              <div>
                <button type="submit" className="xh-btn xh-connect" disabled={loading}>
                  {loading ? "接続中..." : "接続"}
                </button>
              </div>

              {deviceReady && (
                <div className="xh-ready">
                  ✅ デバイスが準備できました
                  <div><button type="button" className="xh-btn xh-start" onClick={handleStart}>再生を開始</button></div>
                </div>
              )}
            </form>
          </div>
        </main>
      </div>
    </>
  );
}
