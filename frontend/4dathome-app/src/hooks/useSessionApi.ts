// src/hooks/useSessionApi.ts
import { preparationApi } from "../services/endpoints";

export async function fetchSessionStatus(sessionId: string) {
  try {
    const res = await preparationApi.getStatus(sessionId);
    return res;
  } catch (error) {
    console.error("fetchSessionStatus failed:", error);
    return null;
  }
}
// ✅ updated to use /api/preparation/status endpoint
