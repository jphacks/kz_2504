// src/pages/PairingPage.tsx (LoginPage として機能)
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { deviceApi } from "../services/endpoints";

/** デバイス認証画面（デバイスハブ製品コード入力: DH001, DH002など） */
export default function PairingPage() {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [deviceReady] = useState(false); // 今回WS使わない
  const wsRef = useRef<WebSocket | null>(null);
  const navigate = useNavigate();

  // デバイス情報取得（GET /api/device/info/{product_code}）→ 成功で /select へ遷移
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const c = code.trim();

    if (!c) { setError("デバイスハブIDを入力してください"); return; }
    if (c.length > 6) { setError("デバイスハブIDは6文字以内で入力してください"); return; }

    setError(null);
    setLoading(true);

    try {
      const data = await deviceApi.getInfo(c);

  // デバイスハブIDを保存（重要: sessionIdとは別管理）
      sessionStorage.setItem("deviceHubId", c);
      if (data?.device_id) sessionStorage.setItem("deviceId", String(data.device_id));
      sessionStorage.setItem("deviceInfo", JSON.stringify(data));

      // 動画選択画面へ遷移（変更: /selectpage → /select）
      navigate("/select", { replace: true });
    } catch (err) {
      console.error(err);
      setError("デバイスが見つからないか、サーバーに接続できません");
      setLoading(false);
    }
  };

  useEffect(() => () => wsRef.current?.close(), []);

  return (
    <>
      <style>{`
        :root{
          --xh-h: clamp(52px, 7vw, 64px);
          --pad: clamp(12px, 3vw, 18px);
          --ico: clamp(22px, 4.8vw, 30px);
          --gap: clamp(14px, 3vw, 22px);
          --logo-h: clamp(32px, 5vw, 44px);
          --logo-w-base: calc(var(--logo-h) * 2);
          --logo-w: max(80px, min(
            var(--logo-w-base),
            calc(100vw - (var(--pad) * 2) - (var(--ico) * 2) - var(--gap) - 12px)
          ));
        }

        .xh-root{ position: fixed; inset:0; color:#fff; }
        .xh-bg{ position:absolute; inset:0; background:url('/PairingPage.jpeg') center/cover no-repeat fixed; }
        .xh-shade{ position:absolute; inset:0; background: radial-gradient(80% 70% at 50% 30%, transparent 0%, rgba(0,0,0,.35) 60%, rgba(0,0,0,.55) 100%); }

        .xh-top{
          position:fixed; inset:0 0 auto 0; height:var(--xh-h);
          background:#000; border-bottom:1px solid rgba(255,255,255,.1);
          z-index:20; padding:0;
        }
        .xh-head{
          width:min(1280px, 92vw);
          margin:0 auto; height:100%;
          display:grid; grid-template-columns:auto 1fr auto; align-items:center; column-gap:12px;
          padding:0 var(--pad);
        }
        .xh-left{ min-width:0; display:flex; align-items:center; }
        .xh-right{ display:flex; align-items:center; gap: calc(var(--gap) + 6px); padding-right: calc(var(--pad) * .6); }

        .xh-logoBox{ width:var(--logo-w); height:var(--logo-h); border-radius:8px; overflow:hidden; border:1px solid rgba(255,255,255,.12); display:grid; place-items:center; background:transparent; }
        .xh-logoImg{ width:100%; height:100%; object-fit:contain; display:block; }

        .xh-ico{ display:flex; align-items:center; justify-content:center; width:auto; height:auto; background:transparent; border:none; border-radius:0; padding:0; }
        .xh-ico img{ width:var(--ico); height:auto; display:block; filter: brightness(0) invert(1); }

        .xh-content-pad{ padding-top: var(--xh-h); }

        .xh-main{ position:relative; min-height:100vh; display:grid; grid-template-rows:var(--xh-h) 1fr; }
        .xh-center{ display:flex; align-items:center; justify-content:center; padding: clamp(12px,4vw,24px); text-align:center; }
        .xh-title{ margin:0 0 10px; font-weight:800; font-size:clamp(18px,3.6vw,28px); text-shadow:0 1px 2px rgba(0,0,0,.35); }
        .xh-field{ width:min(80vw,420px); display:inline-block; }
        .xh-input{ width:100%; height:clamp(40px,6.6vw,48px); background:#fff; color:#111; border-radius:6px; border:2px solid #111; padding:0 12px; font-size:clamp(14px,3.2vw,18px); box-shadow:0 2px 0 rgba(0,0,0,.35); }
        .xh-btn{ margin-top:14px; min-width:160px; height:clamp(42px,7vw,48px); border:none; border-radius:8px; font-weight:700; cursor:pointer; }
        .xh-connect{ background:#fff; color:#111; }
        .xh-debug{ background:#4a90e2; color:#fff; font-size:clamp(13px,2.8vw,15px); }
        .xh-err{ margin-top:8px; color:#ffe08a; }

        @keyframes xh-fadeUp {
          0% { opacity:0; transform: translateY(8px) scale(0.995); filter: blur(4px); }
          100%{ opacity:1; transform:none; filter: none; }
        }
        .xh-fade { animation: xh-fadeUp .6s cubic-bezier(.22,.61,.36,1) both; will-change: transform, opacity, filter; }
        .xh-d0{ animation-delay: .02s; }
        .xh-d1{ animation-delay: .09s; }
        .xh-d2{ animation-delay: .16s; }
        .xh-d3{ animation-delay: .23s; }
        .xh-d4{ animation-delay: .30s; }
        @media (prefers-reduced-motion: reduce) { .xh-fade{ animation:none !important; opacity:1 !important; transform:none !important; filter:none !important; } }
      `}</style>

      <div className="xh-root" aria-live="polite">
        <div className="xh-bg" aria-hidden="true" />
        <div className="xh-shade" aria-hidden="true" />

        <header className="xh-top" role="banner">
          <div className="xh-head">
            <div className="xh-left">
              <div className="xh-logoBox" title="Home">
                <img src="/logg.jpeg" alt="Logo" className="xh-logoImg"
                     onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
              </div>
            </div>
            <div aria-hidden="true" />
            <div className="xh-right">
              <div className="xh-ico" title="System">
                <img src="/system.png" alt="" onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
              </div>
              <div className="xh-ico" title="Notifications">
                <img src="/bell.png" alt="" onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
              </div>
            </div>
          </div>
        </header>

        <main className="xh-main xh-content-pad">
          <div />
          <div className="xh-center">
            <form onSubmit={handleSubmit} aria-labelledby="pairingTitle">
              <h1 id="pairingTitle" className="xh-title xh-fade xh-d0">デバイスハブIDを入力してください</h1>

              <div className="xh-field xh-fade xh-d1">
                <input
                  className="xh-input"
                  value={code}
                  onChange={(e)=>setCode(e.target.value)}
                  placeholder="デバイスハブID（例: DH001）"
                  inputMode="text"
                  autoComplete="one-time-code"
                  maxLength={6}
                />
              </div>

              {error && <div className="xh-err xh-fade xh-d2">⚠ {error}</div>}

              <div className="xh-fade xh-d3">
                <button type="submit" className="xh-btn xh-connect" disabled={loading}>
                  {loading ? "接続中..." : "接続"}
                </button>
              </div>

              {/* デバッグ用：動画に直接飛ぶボタン */}
              <div className="xh-fade xh-d4" style={{marginTop:"12px"}}>
                <button 
                  type="button" 
                  className="xh-btn xh-debug" 
                  onClick={() => navigate("/player?content=sample")}
                >
                  🔧 デバッグ：動画へ直接移動
                </button>
              </div>
            </form>
          </div>
        </main>
      </div>
    </>
  );
}

// ✅ updated for 4DX@HOME spec
