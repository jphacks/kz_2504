export interface SessionInfo {
  session_id: string;
  device_ready: boolean;
}

export type WSOut =
  | { type: "start_playback" }
  | { type: "sync"; time: number }
  | { type: "end_playback" }
  | { type: "select_video"; video: string };

export type WSIn =
  | { type: "ready" }
  | { type: "effect"; action: string }
  | { type: string; [k: string]: any };
