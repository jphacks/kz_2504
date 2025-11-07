import { Routes, Route, Navigate } from "react-router-dom";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import PairingPage from "./pages/PairingPage";
import SelectPage from "./pages/SelectPage";
import PlayerPage from "./pages/PlayerPage";

export default function App() {
  return (
    <Routes>
      {/* 1. ログイン画面 */}
      <Route path="/" element={<LoginPage />} />
      <Route path="/login" element={<LoginPage />} />
      
      {/* 2. 動画選択画面 */}
      <Route path="/select" element={<SelectPage />} />
      
      {/* 3. プレイヤー画面（デバイスハブ＋準備＋再生を統合） */}
      <Route path="/player" element={<PlayerPage />} />
      
      {/* 旧ページ（互換性のためリダイレクト） */}
      <Route path="/home" element={<Navigate to="/" replace />} />
      <Route path="/session" element={<Navigate to="/" replace />} />
      <Route path="/selectpage" element={<Navigate to="/select" replace />} />
    </Routes>
  );
}
 
