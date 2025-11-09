/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_WS_URL?: string;
  readonly VITE_BACKEND_API_URL: string;
  readonly VITE_BACKEND_WS_URL: string;
  // 使ってる環境変数をここに追記（VITE_ で始まるものだけ）
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
