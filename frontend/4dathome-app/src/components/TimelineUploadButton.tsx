import { useState } from "react";
import type { TimelineUploadResponse } from "../types/timeline";
import { loadAndSendTimeline } from "../utils/timeline";

interface TimelineUploadButtonProps {
  sessionId: string;
  videoId: string;
  onComplete?: (result: TimelineUploadResponse) => void;
  onError?: (error: Error) => void;
  className?: string; // ボタンの見た目を外から合わせるため
  onUploadingChange?: (uploading: boolean) => void; // 親へ進捗通知（例：動画一時停止など）
}

export default function TimelineUploadButton({ sessionId, videoId, onComplete, onError, className, onUploadingChange }: TimelineUploadButtonProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<string>("");

  const onClick = async () => { 
    if (uploading) return;
    
    console.log("🔘 [TimelineUploadButton] クリックされました");
    console.log("   Session ID:", sessionId);
    console.log("   Video ID:", videoId);
    
    setUploading(true);
    setProgress("タイムライン読み込み中...");
    try { onUploadingChange?.(true); } catch {}
    try {
      const result = await loadAndSendTimeline(sessionId, videoId);
      setProgress(`送信完了: ${result.transmission_time_ms} ms / events: ${result.events_count}`);
      console.log("✅ [TimelineUploadButton] 送信成功", result);
      onComplete?.(result);
    } catch (e) {
      const err = e as Error;
      setProgress("エラー発生: " + (err.message || String(err)));
      console.error("❌ [TimelineUploadButton] 送信失敗", err);
      onError?.(err);
    } finally {
      setUploading(false);
      try { onUploadingChange?.(false); } catch {}
    }
  };

  return (
    <div>
      <button
        className={`${className ?? "prep-btn prep-btn-primary"} ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
        onClick={onClick}
        disabled={uploading}
      >
        {uploading ? "送信中..." : "タイムライン送信"}
      </button>
      {progress && <div className="prep-status" style={{marginTop: 8}}>{progress}</div>}
    </div>
  );
}
