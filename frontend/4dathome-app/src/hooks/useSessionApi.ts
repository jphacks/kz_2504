// src/hooks/useSessionApi.ts
export async function fetchSessionStatus(id: string) {
  try {
    const res = await fetch(`https://your-server-domain/api/sessions/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data; // { device_ready: true } を想定
  } catch (err) {
    console.error("fetchSessionStatus failed:", err);
    return null;
  }
}
