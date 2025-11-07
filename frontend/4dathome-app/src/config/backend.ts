// 環境変数(Vite)を優先し、未設定時はデフォルトURLにフォールバック
// 最新リビジョン: fdx-home-backend-api-333203798555 (2025/11/7更新)
const DEFAULT_API = "https://fdx-home-backend-api-333203798555.asia-northeast1.run.app";
const DEFAULT_WS = "wss://fdx-home-backend-api-333203798555.asia-northeast1.run.app";

export const BACKEND_API_URL =
	import.meta.env.VITE_BACKEND_API_URL || DEFAULT_API;

export const BACKEND_WS_URL =
	import.meta.env.VITE_BACKEND_WS_URL || DEFAULT_WS;

// ✅ updated for 4DX@HOME spec
