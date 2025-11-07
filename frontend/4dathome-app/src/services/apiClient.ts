// src/services/apiClient.ts
import { BACKEND_API_URL } from "../config/backend";

function join(base: string, path: string) {
  const b = base.replace(/\/$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${b}${p}`;
}

async function handle<T>(res: Response): Promise<T> {
  const ct = res.headers.get("content-type") || "";
  const isJson = ct.includes("application/json");
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      if (isJson) {
        const j = await res.json();
        msg = j?.message || j?.error || msg;
      } else {
        msg = await res.text();
      }
    } catch {
      // noop
    }
    throw new Error(msg);
  }
  return (isJson ? res.json() : (res.text() as any)) as Promise<T>;
}

export const apiClient = {
  get: async <T = any>(path: string, init?: RequestInit): Promise<T> => {
    // 分岐なく一本化: 常にバックエンドのフルURLを直叩き
    const base = BACKEND_API_URL;
    const url = join(base, path);
    const res = await fetch(url, { ...init, method: "GET" });
    return handle<T>(res);
  },
  post: async <T = any>(path: string, body?: any, init?: RequestInit): Promise<T> => {
    // 分岐なく一本化: 常にバックエンドのフルURLを直叩き
    const base = BACKEND_API_URL;
    const url = join(base, path);
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...init,
    });
    return handle<T>(res);
  },
  delete: async <T = any>(path: string, init?: RequestInit): Promise<T> => {
    // 分岐なく一本化: 常にバックエンドのフルURLを直叩き
    const base = BACKEND_API_URL;
    const url = join(base, path);
    const res = await fetch(url, { ...init, method: "DELETE" });
    return handle<T>(res);
  },
};
