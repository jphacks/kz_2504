import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppHeader from "../components/AppHeader";

export default function PairingPage() {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [deviceReady, setDeviceReady] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const navigate = useNavigate();

  // 接続ボタン
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const c = code.trim();
    if (!c) {
      setError("コードを入力してください");
      return;
    }
    setError(null);
    setLoading(true);
    setDeviceReady(false);

    try {
      // APIでセッション確認
      const res = await fetch(`https://your-server-domain/api/sessions/${c}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // デバイスがすでに準備済みならそのままOK
      if (data.device_ready) {
        sessionStorage.setItem("sessionCode", c);
        connectWebSocket(c);
      } else {
        // 準備待ち用にWebSocket接続
        connectWebSocket(c);
      }
    } catch (err) {
      console.error(err);
      setError("セッションが無効か、サーバーに接続できません");
      setLoading(false);
    }
  };

  // WebSocket接続
  const connectWebSocket = (sessionId: string) => {
    try {
      const ws = new WebSocket(`wss://your-server-domain/ws/sessions/${sessionId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("✅ WebSocket接続完了");
        setLoading(false);
      };

      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data);
        console.log("📩 受信:", msg);

        switch (msg.type) {
          case "ready":
            setDeviceReady(true);
            break;
          case "error":
            setError(msg.message || "サーバーエラー");
            break;
        }
      };

      ws.onclose = () => {
        console.log("❌ WebSocket切断");
      };
    } catch (e) {
      console.error("WS接続エラー", e);
      setError("WebSocket接続に失敗しました");
      setLoading(false);
    }
  };

  // 「再生開始」押下
  const handleStart = () => {
    const sessionCode = code.trim();
    if (!sessionCode) return;
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: "start_playback" }));
    }
    sessionStorage.setItem("sessionCode", sessionCode);
    navigate(`/player?session=${encodeURIComponent(sessionCode)}`);
  };

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return (
    <div className="min-h-dvh bg-[#4b00ff] text-white">
      <AppHeader />

      <main className="mx-auto flex max-w-[1280px] items-center justify-center px-4 py-14">
        <form
          onSubmit={handleSubmit}
          className="w-full max-w-xl rounded-2xl border border-white/20 bg-black/20 p-8 backdrop-blur"
        >
          <h1 className="mb-6 text-center text-lg font-medium">ピン番号を打ち込んでください</h1>

          <label className="block text-sm text-white/80 mb-2" htmlFor="session">
            ID
          </label>

          <input
            id="session"
            type="text"
            inputMode="text"
            placeholder="ID"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="w-full rounded-md border border-white/30 bg-white text-black placeholder:text-gray-500 px-3 py-3 text-base outline-none focus:ring-2 focus:ring-white/60"
          />

          {error && <p className="mt-2 text-sm text-yellow-300">{error}</p>}

          {/* 接続ボタン */}
          <div className="mt-6 flex justify-center">
            <button
              type="submit"
              disabled={loading}
              className="min-w-40 rounded-md bg-white px-5 py-2.5 text-black hover:bg-white/90 active:scale-[0.99] disabled:opacity-50"
            >
              {loading ? "接続中..." : "接続"}
            </button>
          </div>

          {/* デバイス準備完了時 */}
          {deviceReady && (
            <div className="mt-6 text-center">
              <p className="mb-3 text-sm text-green-300">✅ デバイスが準備できました</p>
              <button
                type="button"
                onClick={handleStart}
                className="rounded-md bg-green-400 px-6 py-2.5 text-black font-medium hover:bg-green-300"
              >
                再生を開始
              </button>
            </div>
          )}

          <p className="mt-4 text-center text-xs text-white/80">
            開発用テストコード：<code className="font-mono">test</code>
          </p>
        </form>
      </main>
    </div>
  );
}
