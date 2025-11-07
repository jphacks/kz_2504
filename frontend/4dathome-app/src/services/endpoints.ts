// src/services/endpoints.ts
import { apiClient } from "./apiClient";

// Minimal types reused from existing code
export interface TimelineEvent { t: number; type: string; mode?: string; intensity?: number; duration_ms?: number; }
export interface TimelineUploadResponse {
  success: boolean;
  message?: string;
  session_id: string;
  video_id: string;
  size_kb: number;
  events_count: number;
  devices_notified: number;
  transmission_time_ms: number;
}

export const preparationApi = {
  uploadTimeline: (sessionId: string, payload: { video_id: string; timeline_data: { events: TimelineEvent[] } }) =>
    apiClient.post<TimelineUploadResponse>(`/api/preparation/upload-timeline/${encodeURIComponent(sessionId)}`, payload),
  getStatus: (sessionId: string) => apiClient.get(`/api/preparation/status/${encodeURIComponent(sessionId)}`),
};

export const deviceApi = {
  getInfo: (productCode: string) => apiClient.get(`/api/device/info/${encodeURIComponent(productCode)}`),
  register: (req: { product_code: string }) => apiClient.post(`/api/device/register`, req),
  /**
   * デバイステスト実行
   * POST /api/device/test
   * Body: { test_type: string; session_id: string }
   * 期待レスポンス例: { status: "success" | "error"; message?: string; [k: string]: any }
   */
  test: async (testType: string, sessionId: string): Promise<{ status: string; message?: string; [k: string]: any }> => {
    return apiClient.post(`/api/device/test`, {
      test_type: testType,
      session_id: sessionId,
    });
  },
};

export const playbackApi = {
  // スタート信号を送信 (REST API + WebSocket)
  sendStartSignal: async (sessionId: string, options: { hubId?: string } = {}) => {
    console.log("▶️ [API] sendStartSignal", { sessionId, options });
    try {
      const response = await apiClient.post(`/api/playback/start/${encodeURIComponent(sessionId)}`, null, {
        headers: { "Content-Type": "application/json" },
      });
      console.log("✅ [API] sendStartSignal SUCCEEDED", { status: response.status, data: response.data });
      return { ok: true, data: response.data };
    } catch (error) {
      console.error("❌ [API] sendStartSignal FAILED", { error });
      return { ok: false, error };
    }
  },

  // ストップ信号を送信 (REST API + WebSocket)
  sendStopSignal: async (sessionId: string, options: { hubId?: string } = {}) => {
    console.log("⏹️ [API] sendStopSignal", { sessionId, options });
    try {
      const response = await apiClient.post(`/api/playback/stop/${encodeURIComponent(sessionId)}`, null, {
        headers: { "Content-Type": "application/json" },
      });
      console.log("✅ [API] sendStopSignal SUCCEEDED", { status: response.status, data: response.data });
      return { ok: true, data: response.data };
    } catch (error) {
      console.error("❌ [API] sendStopSignal FAILED", { error });
      return { ok: false, error };
    }
  },

  // 現在の再生状態を取得
  getStatus: async () => {
    console.log("ℹ️ [API] getStatus");
    try {
      const response = await apiClient.get(`/api/playback/status`);
      console.log("✅ [API] getStatus SUCCEEDED", { data: response.data });
      return { ok: true, data: response.data };
    } catch (error) {
      console.error("❌ [API] getStatus FAILED", { error });
      return { ok: false, error };
    }
  },

  // 現在接続中のクライアント一覧を取得
  getConnections: async () => {
    console.log("ℹ️ [API] getConnections");
    try {
      const response = await apiClient.get(`/api/playback/connections`);
      console.log("✅ [API] getConnections SUCCEEDED", { data: response.data });
      return { ok: true, data: response.data };
    } catch (error) {
      console.error("❌ [API] getConnections FAILED", { error });
      return { ok: false, error };
    }
  },
};

