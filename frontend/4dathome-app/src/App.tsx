import { Routes, Route, Navigate } from "react-router-dom";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import PairingPage from "./pages/PairingPage";
import SelectPage from "./pages/SelectPage";
import PlayerPage from "./pages/PlayerPage";
import VideoPreparationPage from "./pages/VideoPreparationPage";
import ProtectedRoute from "./components/ProtectedRoute";

export default function App() {
  return (
    <Routes>
  {/* 1. 初期表示はHomePage（動画再生） */}
  <Route path="/" element={<HomePage />} />
  <Route path="/login" element={<LoginPage />} />
      
  {/* 2. 動画選択画面 */}
  <Route path="/select" element={<SelectPage />} />

  {/* 準備（認証/接続/テスト）画面 */}
  <Route path="/prepare" element={<ProtectedRoute><VideoPreparationPage /></ProtectedRoute>} />
      
  {/* 3. プレイヤー画面（準備済みでアクセス） */}
  <Route path="/player" element={<ProtectedRoute><PlayerPage /></ProtectedRoute>} />
      
      {/* 旧ページ（互換性のためリダイレクト） */}
      <Route path="/home" element={<Navigate to="/" replace />} />
      <Route path="/session" element={<Navigate to="/" replace />} />
      <Route path="/selectpage" element={<Navigate to="/select" replace />} />
    </Routes>
  );
}
 
