import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { BACKEND_WS_URL } from "../config/backend";
import { deviceApi, preparationApi } from "../services/endpoints";
import { fetchSessionStatus } from "../hooks/useSessionApi";


type StepKey = "session" | "device" | "videoLoad" | "timeline" | "deviceTest";
type StepStatus = "idle" | "loading" | "done";


type SelectedVideo = {
  id: string;
  title: string;
  thumbnailUrl: string;
};

// localStorage履歴管理ヘルパー
function pushRecent(key: string, value: string, max = 5) {
  const trimmed = value.trim();
  if (!trimmed) return;

  try {
    const raw = localStorage.getItem(key);
    const list: string[] = raw ? JSON.parse(raw) : [];
    const withoutDup = list.filter((v) => v !== trimmed);
    const updated = [trimmed, ...withoutDup].slice(0, max);
    localStorage.setItem(key, JSON.stringify(updated));
  } catch {
    // 失敗時は無視
  }
}

function loadRecent(key: string): string[] {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}


// 共通ボタンコンポーネント
type PrepButtonProps = {
  label: string;
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
};

function PrepButton({ label, onClick, type = "button", disabled }: PrepButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className="prep-btn"
      style={{
        width: "100%",
        height: 42,
        borderRadius: 8,
        border: "none",
        fontWeight: 700,
        fontSize: 14,
        cursor: disabled ? "not-allowed" : "pointer",
        background: "#ffffff",
        color: "#111111",
        boxShadow: "0 2px 0 rgba(0, 0, 0, 0.3)",
        opacity: disabled ? 0.6 : 1,
      }}
    >
      {label}
    </button>
  );
}

// タイムラインファイル名解決ヘルパー
function resolveTimelineFileId(videoId: string): string {
  switch (videoId) {
    case "main":
      // 実ファイル: public/json/main.json
      return "main";
    case "demo1":
      return "demo1";
    case "demo2":
      return "demo2";
    case "demo3":
      return "demo3";
    // 将来の動画IDはここに追加
    default:
      return videoId;
  }
}

// 状態アイコン（赤ドーナツリング → 緑チェック）
function StatusIcon({ status }: { status: StepStatus }) {
  if (status === "done") {
    return (
      <span
        className="prep-icon prep-icon--done"
        aria-label="完了"
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 18,
          height: 18,
          borderRadius: 999,
          backgroundColor: "#16a34a",
          color: "#fff",
          fontSize: 11,
          fontWeight: 700,
        }}
      >
        ✓
      </span>
    );
  }

  if (status === "loading") {
    return (
      <span
        className="prep-icon prep-icon--ring prep-icon--spin"
        aria-label="処理中"
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 18,
          height: 18,
          borderRadius: 999,
          border: "2px solid rgba(255, 75, 75, 0.35)",
          borderTopColor: "#ff4b4b",
          boxSizing: "border-box",
          animation: "prep-spin 0.8s linear infinite",
        }}
      />
    );
  }

  // idle
  return (
    <span
      className="prep-icon prep-icon--ring"
      aria-label="未完了"
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 18,
        height: 18,
        borderRadius: 999,
        border: "2px solid #ff4b4b",
        boxSizing: "border-box",
      }}
    />
  );
}

// ①・② 用: ラベル + 入力行（input / 送信ボタンのみ、アイコンなし）+ 履歴候補
interface PrepRowWithInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  isLoading?: boolean;
  recentList?: string[];
}

function PrepRowWithInput({ label, value, onChange, onSubmit, placeholder, isLoading, recentList }: PrepRowWithInputProps) {
  return (
    <div className="prep-section-block" style={{ padding: "12px 0", borderBottom: "1px solid rgba(255,255,255,0.12)" }}>
      {/* ラベル行 */}
      <div style={{ fontSize: 13, opacity: 0.9, marginBottom: 8 }}>{label}</div>
      
      {/* 入力行: input / 送信ボタン（アイコンなし） */}
      <div
        className="prep-row"
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) 120px",
          alignItems: "center",
          gap: 12,
        }}
      >
        <input
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          style={{
            width: "100%",
            height: 40,
            background: "#fff",
            color: "#111",
            borderRadius: 6,
            border: "2px solid #111",
            padding: "0 12px",
            fontSize: 15,
          }}
        />
        
        <PrepButton
          label={isLoading ? "送信中..." : "送信"}
          onClick={onSubmit}
          disabled={isLoading}
        />
      </div>

      {/* 履歴候補ボタン */}
      {recentList && recentList.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>最近使ったID:</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {recentList.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => onChange(item)}
                style={{
                  padding: "4px 10px",
                  borderRadius: 4,
                  background: "rgba(255,255,255,0.1)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  color: "#fff",
                  fontSize: 12,
                  cursor: "pointer",
                  fontWeight: 500,
                }}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ③〜⑤ 用: 1行（アイコン / ラベル / 再実行ボタン）
interface PrepRowActionProps {
  status: StepStatus;
  label: string;
  actionLabel: string;
  onClick: () => void;
}

function PrepRowAction({ status, label, actionLabel, onClick }: PrepRowActionProps) {
  return (
    <div className="prep-section-block" style={{ padding: "12px 0", borderBottom: "1px solid rgba(255,255,255,0.12)" }}>
      <div
        className="prep-row"
        style={{
          display: "grid",
          gridTemplateColumns: "32px minmax(0, 1fr) 120px",
          alignItems: "center",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          <StatusIcon status={status} />
        </div>
        
        <span style={{ fontSize: 15, fontWeight: 600, color: "#fff" }}>{label}</span>
        
        <PrepButton
          label={status === "loading" ? "処理中..." : actionLabel}
          onClick={onClick}
          disabled={status === "loading" || status === "done"}
        />
      </div>
    </div>
  );
}

// ...existing code...


export default function VideoPreparationPage() {
  const { search } = useLocation();
  const q = useMemo(() => new URLSearchParams(search), [search]);
  const navigate = useNavigate();

  // 選択された動画ID（クエリから取得）
  const contentId = q.get("content") || "demo1";
  
  console.log('📝 VideoPreparationPage loaded with contentId:', contentId);

  const [sessionId, setSessionId] = useState("");
  const [deviceHubId, setDeviceHubId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [selectedVideo, setSelectedVideo] = useState<SelectedVideo | null>(null);

  // 履歴候補
  const [recentSessions, setRecentSessions] = useState<string[]>([]);
  const [recentHubs, setRecentHubs] = useState<string[]>([]);

  // 5つのステップの状態管理
  const [steps, setSteps] = useState<Record<StepKey, StepStatus>>({
    session: "idle",
    device: "idle",
    videoLoad: "idle",
    timeline: "idle",
    deviceTest: "idle",
  });

  const wsRef = useRef<WebSocket | null>(null);

  // sessionStorageから選択中の動画情報を読み込む
  useEffect(() => {
    const raw = sessionStorage.getItem("selectedVideo");
    if (!raw) {
      console.warn("No selectedVideo in sessionStorage");
      return;
    }
    try {
      const parsed = JSON.parse(raw) as SelectedVideo;
      setSelectedVideo(parsed);
    } catch (e) {
      console.error("Failed to parse selectedVideo:", e);
    }
  }, []);

  // localStorageから履歴候補を読み込む
  useEffect(() => {
    setRecentSessions(loadRecent("recentSessionIds"));
    setRecentHubs(loadRecent("recentDeviceHubIds"));
  }, []);

  // PairingPageと同じ通信パターンに統一したステップ実行関数
  const runStep = async (key: StepKey, action: () => Promise<void>) => {
    // すでにloading中なら二重実行しない
    if (steps[key] === "loading") return;

    setSteps((prev) => ({ ...prev, [key]: "loading" }));
    setError(null);
    
    try {
      await action(); // ここで通信 or 非同期処理を待つ
      setSteps((prev) => ({ ...prev, [key]: "done" }));
    } catch (err: any) {
      console.error(`[${key}] step failed`, err);
      setSteps((prev) => ({ ...prev, [key]: "idle" }));
      setError(err?.message || String(err));
    }
  };

  // ③動画読み込み: ①②完了後に自動実行
  useEffect(() => {
    if (
      steps.session === "done" &&
      steps.device === "done" &&
      steps.videoLoad === "idle" &&
      selectedVideo
    ) {
      handleVideoLoad();
    }
  }, [steps.session, steps.device, steps.videoLoad, selectedVideo]);

  // ④タイムライン送信: ③完了後に自動実行
  useEffect(() => {
    if (
      steps.videoLoad === "done" &&
      steps.timeline === "idle" &&
      selectedVideo &&
      sessionId
    ) {
      handleTimeline();
    }
  }, [steps.videoLoad, steps.timeline, selectedVideo, sessionId]);

  // ⑤デバイス動作確認: ④完了後に自動実行
  useEffect(() => {
    if (
      steps.timeline === "done" &&
      steps.deviceTest === "idle" &&
      sessionId &&
      steps.device === "done"
    ) {
      handleDeviceTest();
    }
  }, [steps.timeline, steps.deviceTest, sessionId, steps.device]);

  // ①セッションIDステップ: ボタン押下時に実行（PairingPageパターン）
  const handleSessionId = () => {
    const sid = sessionId.trim();
    if (!sid) {
      setError("セッションIDを入力してください");
      return;
    }

    runStep("session", async () => {
      // セッションIDの検証・通信処理（fetchSessionStatusを使用）
      await fetchSessionStatus(sid); // 通信は行うが結果は問わない
      // 単純にID保存・履歴追加だけ
      sessionStorage.setItem("sessionId", sid);
      pushRecent("recentSessionIds", sid);
      setRecentSessions(loadRecent("recentSessionIds"));
    });
  };

  // ②デバイスIDステップ: ボタン押下時に実行（PairingPageと同じdeviceApi.getInfo）
  const handleDeviceId = () => {
    const hub = deviceHubId.trim();
    if (!hub) {
      setError("デバイスIDを入力してください");
      return;
    }

    runStep("device", async () => {
      // PairingPageと同じAPI呼び出し
      const data = await deviceApi.getInfo(hub);
      
      // 成功時: sessionStorageに保存 & 履歴に追加
      sessionStorage.setItem("deviceHubId", hub);
      if (data?.device_id) {
        sessionStorage.setItem("deviceId", String(data.device_id));
      }
      sessionStorage.setItem("deviceInfo", JSON.stringify(data));
      pushRecent("recentDeviceHubIds", hub);
      setRecentHubs(loadRecent("recentDeviceHubIds"));
    });
  };

  // ③動画読み込みステップ: 手動リトライ & 自動実行用
  const handleVideoLoad = () => {
    if (!selectedVideo) {
      setError("動画が選択されていません");
      return;
    }

    runStep("videoLoad", async () => {
      // 動画の準備に必要な通信処理
      // TODO: 実際のAPI実装時に置き換え
      await new Promise((resolve) => setTimeout(resolve, 800));
    });
  };

  // ④タイムライン送信ステップ: 手動リトライ & 自動実行用
  const handleTimeline = () => {
    if (!selectedVideo) {
      setError("動画が選択されていません");
      return;
    }
    if (!sessionId) {
      setError("セッションIDが設定されていません");
      return;
    }

    runStep("timeline", async () => {
      // タイムラインJSONをローカルから取得
      const videoId = selectedVideo.id;
      const fileId = resolveTimelineFileId(videoId);
      const jsonUrl = `/json/${fileId}.json`;
      
      console.log(`[timeline] fetching local JSON from ${jsonUrl}`);
      const res = await fetch(jsonUrl);
      if (!res.ok) {
        throw new Error(`Failed to fetch timeline JSON: ${res.status}`);
      }
      
      // Content-Typeチェック: HTMLが返ってきていないか確認
      const contentType = res.headers.get("content-type");
      if (contentType && !contentType.includes("application/json")) {
        console.error(`[timeline] Unexpected content-type: ${contentType}`);
        throw new Error(`Expected JSON but got ${contentType}`);
      }
      
      const timelineJson = await res.json();
      console.log("[timeline] fetched local JSON", timelineJson);

      // 配列だけの場合は { events: [...] } に wrap
      const wrapped = Array.isArray(timelineJson)
        ? { events: timelineJson }
        : timelineJson;

      // デバッグログ
      console.log("[timeline] POST payload check", {
        url: `/api/preparation/upload-timeline/${sessionId}`,
        videoId,
        fileId,
        hasEvents: !!wrapped?.events,
        eventCount: wrapped?.events?.length,
      });

      // タイムラインJSONをバックエンドにPOST
      const result = await preparationApi.uploadTimeline(sessionId, videoId, wrapped);
      console.log("[timeline] upload done", result);
    });
  };

  // ⑤デバイス動作確認ステップ: 手動リトライ & 自動実行用
  const handleDeviceTest = () => {
    if (!sessionId) {
      setError("セッションIDが設定されていません");
      return;
    }
    if (steps.device !== "done") {
      setError("先にデバイスを接続してください");
      return;
    }

    runStep("deviceTest", async () => {
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
        @keyframes prep-spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
      
      <div
        style={{
          minHeight: "100vh",
          background: "#0b0f1a url('/prepare.jpeg') center/cover no-repeat fixed",
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
          {selectedVideo && (
            <div
              style={{
                padding: "12px 0 14px",
                borderBottom: "1px solid rgba(255,255,255,0.08)",
                marginBottom: 14,
              }}
            >
              <div style={{ fontSize: 13, opacity: 0.9, marginBottom: 6 }}>選択中の動画</div>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <img
                  src={selectedVideo.thumbnailUrl}
                  alt={selectedVideo.title}
                  style={{
                    width: 80,
                    height: 45,
                    borderRadius: 4,
                    objectFit: "cover",
                  }}
                  onError={(e) => {
                    (e.currentTarget as HTMLImageElement).style.display = "none";
                  }}
                />
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>
                    {selectedVideo.title}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 入力フィールド → 削除（PrepRowWithInputに統合） */}

          {/* ステップ表示（新レイアウト） */}
          <div style={{ marginBottom: 20 }}>
            {/* ① セッションID ブロック（アイコンなし + 履歴候補） */}
            <PrepRowWithInput
              label="セッションID"
              value={sessionId}
              onChange={setSessionId}
              onSubmit={handleSessionId}
              placeholder="例: session01"
              isLoading={steps.session === "loading"}
              recentList={recentSessions}
            />

            {/* ② デバイスハブID ブロック（アイコンなし + 履歴候補） */}
            <PrepRowWithInput
              label="デバイスID（ハブID）"
              value={deviceHubId}
              onChange={setDeviceHubId}
              onSubmit={handleDeviceId}
              placeholder="例: DH001"
              isLoading={steps.device === "loading"}
              recentList={recentHubs}
            />

            {/* ③ 動画読み込み */}
            <PrepRowAction
              status={steps.videoLoad}
              label="動画読み込み"
              actionLabel="再読込み"
              onClick={handleVideoLoad}
            />

            {/* ④ タイムライン送信 */}
            <PrepRowAction
              status={steps.timeline}
              label="タイムライン送信"
              actionLabel="再送信"
              onClick={handleTimeline}
            />

            {/* ⑤ デバイス動作確認 */}
            <PrepRowAction
              status={steps.deviceTest}
              label="デバイス動作確認"
              actionLabel="再送信"
              onClick={handleDeviceTest}
            />
          </div>

          {/* エラー表示 */}
          {error && (
            <div style={{ marginBottom: 14, fontSize: 12, color: "#ff9f9f" }}>⚠ {error}</div>
          )}

          {/* 再生開始ボタン（PairingPage の接続ボタンと同じスタイル） */}
          <button
            onClick={handleStart}
            disabled={!allReady}
            style={{
              width: "100%",
              height: "clamp(46px, 7vw, 52px)",
              borderRadius: 8,
              fontWeight: 700,
              fontSize: 16,
              background: allReady ? "#fff" : "#333",
              color: allReady ? "#111" : "#666",
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
