import { useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { BACKEND_WS_URL } from "../config/backend";
import { deviceApi } from "../services/endpoints";

type StepKey = "session" | "device" | "videoLoad" | "timeline" | "deviceTest";
type StepStatus = "idle" | "loading" | "done";

interface PrepareStepItemProps {
  label: string;
  status: StepStatus;
  onClick: () => void;
  disabled?: boolean;
}

function PrepareStepItem({ label, status, onClick, disabled }: PrepareStepItemProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || status === "done"}
      style={{
        width: "100%",
        display: "grid",
        gridTemplateColumns: "1fr auto",
        alignItems: "center",
        gap: 12,
        padding: "14px 16px",
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 8,
        color: "#fff",
        fontSize: 15,
        fontWeight: 600,
        cursor: disabled || status === "done" ? "not-allowed" : "pointer",
        transition: "all 0.2s ease",
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <span style={{ textAlign: "left" }}>{label}</span>
      <StatusIndicator status={status} />
    </button>
  );
}

function StatusIndicator({ status }: { status: StepStatus }) {
  if (status === "idle") {
    return <div style={{ width: 20, height: 20, borderRadius: "50%", background: "#ff4444" }} />;
  }
  if (status === "loading") {
    return (
      <div
        style={{
          width: 20,
          height: 20,
          border: "3px solid #4ade80",
          borderTopColor: "transparent",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
      />
    );
  }
  // done
  return (
    <div
      style={{
        width: 20,
        height: 20,
        borderRadius: "50%",
        background: "#4ade80",
        display: "grid",
        placeItems: "center",
        fontSize: 12,
        fontWeight: 900,
        color: "#000",
      }}
    >
      ✓
    </div>
  );
}


export default function VideoPreparationPage() {
  const { search } = useLocation();
  const q = useMemo(() => new URLSearchParams(search), [search]);
  const navigate = useNavigate();

  // 選択された動画ID（クエリから取得）
  const contentId = q.get("content") || "demo1";
  const videoTitle = contentId.toUpperCase();
  
  console.log('📝 VideoPreparationPage loaded with contentId:', contentId);

  const [sessionId, setSessionId] = useState("");
  const [deviceHubId, setDeviceHubId] = useState("");
  const [error, setError] = useState<string | null>(null);

  // 5つのステップの状態管理
  const [steps, setSteps] = useState<Record<StepKey, StepStatus>>({
    session: "idle",
    device: "idle",
    videoLoad: "idle",
    timeline: "idle",
    deviceTest: "idle",
  });

  const wsRef = useRef<WebSocket | null>(null);

  // ステップ実行のヘルパー
  const handleStep = async (key: StepKey, action: () => Promise<void>) => {
    setSteps((s) => ({ ...s, [key]: "loading" }));
    setError(null);
    try {
      await action();
      setSteps((s) => ({ ...s, [key]: "done" }));
    } catch (e: any) {
      setSteps((s) => ({ ...s, [key]: "idle" }));
      setError(e?.message || String(e));
    }
  };

  // 1. セッションID
  const handleSessionId = async () => {
    await handleStep("session", async () => {
      if (!sessionId.trim()) throw new Error("セッションIDを入力してください");
      sessionStorage.setItem("sessionId", sessionId.trim());
      await new Promise((resolve) => setTimeout(resolve, 500));
    });
  };

  // 2. デバイスID（WebSocket接続）
  const handleDeviceId = async () => {
    await handleStep("device", async () => {
      const sid = sessionId.trim();
      const hub = deviceHubId.trim();
      if (!sid) throw new Error("先にセッションIDを設定してください");

      const url = hub
        ? `${BACKEND_WS_URL}/api/playback/ws/sync/${encodeURIComponent(sid)}?hub=${encodeURIComponent(hub)}`
        : `${BACKEND_WS_URL}/api/playback/ws/sync/${encodeURIComponent(sid)}`;

      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {}
        wsRef.current = null;
      }

      const ws = new WebSocket(url);
      wsRef.current = ws;

      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error("接続タイムアウト")), 5000);
        ws.onopen = () => {
          if (hub && ws.readyState === WebSocket.OPEN) {
            try {
              ws.send(JSON.stringify({ type: "identify", hub_id: hub }));
            } catch {}
          }
          clearTimeout(timeout);
          setTimeout(resolve, 600);
        };
        ws.onerror = () => {
          clearTimeout(timeout);
          reject(new Error("WebSocket接続エラー"));
        };
      });

      if (hub) sessionStorage.setItem("deviceHubId", hub);
    });
  };

  // 3. 動画読み込み（ダミー）
  const handleVideoLoad = async () => {
    await handleStep("videoLoad", async () => {
      await new Promise((resolve) => setTimeout(resolve, 800));
    });
  };

  // 4. タイムライン送信（ダミー）
  const handleTimeline = async () => {
    await handleStep("timeline", async () => {
      if (!sessionId.trim()) throw new Error("先にセッションIDを設定してください");
      // 実際のタイムライン送信処理をここに実装
      await new Promise((resolve) => setTimeout(resolve, 1000));
    });
  };

  // 5. デバイス動作確認
  const handleDeviceTest = async () => {
    await handleStep("deviceTest", async () => {
      if (!sessionId.trim()) throw new Error("セッションIDが設定されていません");
      if (steps.timeline !== "done") throw new Error("先にタイムラインを送信してください");
      if (steps.device !== "done") throw new Error("先にデバイスを接続してください");

      const result = await deviceApi.test("basic", sessionId);
      if (result?.status?.toLowerCase?.() !== "success") {
        throw new Error(result?.message || `status: ${result?.status}`);
      }
    });
  };

  // 全ステップ完了チェック
  const allReady = Object.values(steps).every((s) => s === "done");

  const handleStart = () => {
    const params = new URLSearchParams();
    params.set("session", sessionId.trim());
    if (deviceHubId.trim()) params.set("hub", deviceHubId.trim());
    params.set("content", contentId);

    navigate(`/player?${params.toString()}`);
  };

  return (
    <>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
      
      <div
        style={{
          minHeight: "100vh",
          background: "#0b0f1a",
          display: "grid",
          placeItems: "center",
          color: "#fff",
          padding: "20px 0",
        }}
      >
        <div
          style={{
            width: "min(640px, 92%)",
            background: "rgba(16,20,32,0.9)",
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 14,
            padding: "clamp(18px, 3.5vw, 28px)",
          }}
        >
          <h2
            style={{
              fontWeight: 800,
              fontSize: "clamp(18px, 3.6vw, 22px)",
              margin: "0 0 20px",
            }}
          >
            再生準備
          </h2>

          {/* 選択中の動画 */}
          <div
            style={{
              padding: "12px 0 14px",
              borderBottom: "1px solid rgba(255,255,255,0.08)",
              marginBottom: 14,
            }}
          >
            <div style={{ fontSize: 13, opacity: 0.9, marginBottom: 6 }}>選択中の動画</div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div
                style={{
                  width: 80,
                  height: 45,
                  background: "#1a1f2e",
                  borderRadius: 4,
                  display: "grid",
                  placeItems: "center",
                  fontSize: 10,
                  color: "#666",
                }}
              >
                {videoTitle}
              </div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{videoTitle}.mp4</div>
            </div>
          </div>

          {/* 入力フィールド */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 13, opacity: 0.9, marginBottom: 6 }}>セッションID</div>
            <input
              placeholder="例: session01"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              style={{
                width: "100%",
                height: "clamp(40px, 6.6vw, 48px)",
                background: "#fff",
                color: "#111",
                borderRadius: 6,
                border: "2px solid #111",
                padding: "0 12px",
                fontSize: 15,
              }}
            />
          </div>

          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 13, opacity: 0.9, marginBottom: 6 }}>デバイスID（ハブID）</div>
            <input
              placeholder="例: DH001"
              value={deviceHubId}
              onChange={(e) => setDeviceHubId(e.target.value)}
              style={{
                width: "100%",
                height: "clamp(40px, 6.6vw, 48px)",
                background: "#fff",
                color: "#111",
                borderRadius: 6,
                border: "2px solid #111",
                padding: "0 12px",
                fontSize: 15,
              }}
            />
          </div>

          {/* ステップボタン */}
          <div style={{ display: "grid", gap: 10, marginBottom: 20 }}>
            <PrepareStepItem label="1. セッションID" status={steps.session} onClick={handleSessionId} />
            <PrepareStepItem label="2. デバイスID" status={steps.device} onClick={handleDeviceId} />
            <PrepareStepItem label="3. 動画読み込み" status={steps.videoLoad} onClick={handleVideoLoad} />
            <PrepareStepItem label="4. タイムライン送信" status={steps.timeline} onClick={handleTimeline} />
            <PrepareStepItem label="5. デバイス動作確認" status={steps.deviceTest} onClick={handleDeviceTest} />
          </div>

          {/* エラー表示 */}
          {error && (
            <div style={{ marginBottom: 14, fontSize: 12, color: "#ff9f9f" }}>⚠ {error}</div>
          )}

          {/* 再生開始ボタン */}
          <button
            onClick={handleStart}
            disabled={!allReady}
            style={{
              width: "100%",
              height: "clamp(46px, 7vw, 52px)",
              borderRadius: 8,
              fontWeight: 700,
              fontSize: 16,
              background: allReady ? "#4ade80" : "#333",
              color: allReady ? "#000" : "#666",
              border: "none",
              cursor: allReady ? "pointer" : "not-allowed",
              transition: "all 0.2s ease",
              opacity: allReady ? 1 : 0.5,
              marginBottom: 12,
            }}
          >
            動画を再生する
          </button>

          {/* テスト用: 準備スキップして再生画面へ */}
          <button
            onClick={() => {
              const params = new URLSearchParams();
              params.set("session", sessionId.trim());
              if (deviceHubId.trim()) params.set("hub", deviceHubId.trim());
              params.set("content", contentId);
              navigate(`/player?${params.toString()}`);
            }}
            style={{
              width: "100%",
              height: "clamp(38px, 6vw, 42px)",
              borderRadius: 8,
              fontWeight: 600,
              background: "rgba(74,144,226,0.2)",
              color: "#4a90e2",
              border: "1px solid #4a90e2",
            }}
          >
            テスト: 準備をスキップして再生画面へ
          </button>
        </div>
      </div>
    </>
  );
}
