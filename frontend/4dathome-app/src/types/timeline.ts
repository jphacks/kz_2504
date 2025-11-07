export interface TimelineEvent {
  t: number;           // 秒
  type: string;        // vibration / flash / wind / water / color など
  mode?: string;       // long / strong / heartbeat / strobe / burst / steady 等
  intensity?: number;  // 0..1 目安
  duration_ms?: number;// ミリ秒
}

export interface TimelineUploadRequest {
  video_id: string;
  timeline_data: { events: TimelineEvent[] };
}

export interface TimelineUploadResponse {
  success: boolean;
  message: string;
  session_id: string;
  video_id: string;
  size_kb: number;
  events_count: number;
  devices_notified: number;
  transmission_time_ms: number;
}
