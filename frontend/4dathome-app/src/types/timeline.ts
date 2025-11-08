// 新しいタイムラインイベント形式（start/stop + caption対応）
export type EffectType = "vibration" | "flash" | "wind" | "water" | "color";

export type EffectEvent = {
  t: number;
  action: "start" | "stop";
  effect: EffectType;
  mode: string;
};

export type CaptionEvent = {
  t: number;
  action: "caption";
  text: string;
};

export type TimelineEvent = EffectEvent | CaptionEvent;

export type ActiveEffects = {
  vibration: boolean;
  flash: boolean;
  wind: boolean;
  water: boolean;
  color: boolean;
};

// 旧形式（互換性のため残す）
export interface LegacyTimelineEvent {
  t: number;           // 秒
  type: string;        // vibration / flash / wind / water / color など
  mode?: string;       // long / strong / heartbeat / strobe / burst / steady 等
  intensity?: number;  // 0..1 目安
  duration_ms?: number;// ミリ秒
}

export interface TimelineUploadRequest {
  video_id: string;
  timeline_data: { events: LegacyTimelineEvent[] };
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
