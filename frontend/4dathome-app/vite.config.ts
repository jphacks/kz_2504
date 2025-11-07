import { defineConfig, loadEnv } from "vite";
// @ts-ignore Node globals are available in Vite config runtime
declare const process: any;
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.VITE_BACKEND_API_URL ;
  console.log("[vite] proxy target:", target); // ★これ追加

  return {
    plugins: [react()],
    optimizeDeps: { entries: ["src/main.tsx"] }, // 入口を限定
    server: {
      proxy: {
        "/api": {
          target,
          changeOrigin: true,
          secure: true,
          ws: true,
        },
      },
    },
  };
});
