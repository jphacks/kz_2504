import { useState } from "react";
import type { TimelineUploadResponse } from "../types/timeline";
import { loadAndSendTimeline } from "../utils/timeline";

interface TimelineUploadButtonProps {
  sessionId: string;
  videoId: string;
  onComplete?: (result: TimelineUploadResponse) => void;
  onError?: (error: Error) => void;
}

export default function TimelineUploadButton({ sessionId, videoId, onComplete, onError }: TimelineUploadButtonProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<string>("");

  const onClick = async () => {
    if (uploading) return;
    setUploading(true);
    setProgress("タイムライン読み込み中...");
    try {
      const result = await loadAndSendTimeline(sessionId, videoId);
      setProgress(`送信完了: ${result.transmission_time_ms} ms / events: ${result.events_count}`);
      onComplete?.(result);
    } catch (e) {
      const err = e as Error;
      setProgress("エラー発生: " + (err.message || String(err)));
      onError?.(err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <button
        className={`prep-btn prep-btn-primary ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
        onClick={onClick}
        disabled={uploading}
      >
        {uploading ? "送信中..." : "送信"}
      </button>
      {progress && <div className="prep-status" style={{marginTop: 8}}>{progress}</div>}
    </div>
  );
}
