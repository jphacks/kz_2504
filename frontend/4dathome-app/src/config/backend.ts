// 環境変数(Vite)を優先し、未設定時はデフォルトURLにフォールバック
// デフォルトURLはプレースホルダー（実際のURLは.envファイルで指定してください）
const DEFAULT_API = "https://your-backend-api.run.app";
const DEFAULT_WS = "wss://your-backend-api.run.app";

export const BACKEND_API_URL =
	import.meta.env.VITE_BACKEND_API_URL || DEFAULT_API;

export const BACKEND_WS_URL =
	import.meta.env.VITE_BACKEND_WS_URL || DEFAULT_WS;

// ✅ updated for 4DX@HOME spec
