// src/hooks/useSessionApi.ts
import { BACKEND_API_URL } from "../config/backend";

export async function fetchSessionStatus(id: string) {
  try {
    const res = await fetch(`${BACKEND_API_URL}/api/sessions/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data; // { device_ready: true } を想定
  } catch (err) {
    console.error("fetchSessionStatus failed:", err);
    return null;
  }
}
// ✅ updated for 4DX@HOME spec
