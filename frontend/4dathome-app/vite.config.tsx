import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "", "");
  // 開発時の /api プロキシ先
  const apiTarget = env.VITE_BACKEND_API_URL || "https://fdx-home-backend-api-47te6uxkwa-an.a.run.app";

  return {
    plugins: [react()],
    optimizeDeps: { entries: ["src/main.tsx"] },
    server: {
      port: 5175,           // CORS 許可先に合わせてポート固定
      strictPort: true,     // 使用中でも他ポートへ逃げない
      proxy: {
        // フロントからは相対 /api を叩き、Vite がバックエンドへ中継
        "/api": {
          target: apiTarget,
          changeOrigin: true,
          ws: false,
          // 明示的なパス書き換えは不要（/api をそのまま）
        },
      },
    },
  };
});
