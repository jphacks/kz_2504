const API_BASE = import.meta.env.VITE_API_BASE_URL || window.location.origin;

export async function getSession(id: string) {
  try {
    const r = await fetch(`${API_BASE}/api/sessions/${encodeURIComponent(id)}`);
    if (!r.ok) throw new Error(String(r.status));
    return (await r.json()) as { device_ready: boolean };
  } catch (e) {
    // ★ サーバー未整備でも試せるデモ挙動（id === "test" でOK）
    return { device_ready: id.toLowerCase() === "test" };
  }
}
