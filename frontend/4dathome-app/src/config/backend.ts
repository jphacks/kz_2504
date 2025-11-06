// 環境変数（Vite）を優先し、未設定時はデフォルトURLにフォールバック
const DEFAULT_API = "https://fdx-home-backend-api-47te6uxkwa-an.a.run.app";
const DEFAULT_WS = "wss://fdx-home-backend-api-47te6uxkwa-an.a.run.app";

export const BACKEND_API_URL =
	import.meta.env.VITE_BACKEND_API_URL || DEFAULT_API;

export const BACKEND_WS_URL =
	import.meta.env.VITE_BACKEND_WS_URL || DEFAULT_WS;

// ✅ updated for 4DX@HOME spec
