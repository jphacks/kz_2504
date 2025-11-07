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
  sendTime: (body: { sessionId: string; deviceHubId?: string; currentTime: number; timestamp?: number }) =>
    apiClient.post(`/api/v1/playback/time`, body),
};
