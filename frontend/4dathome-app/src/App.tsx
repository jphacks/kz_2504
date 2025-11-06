import { Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import PairingPage from "./pages/PairingPage";
import SelectPage from "./pages/SelectPage";
import PlayerPage from "./pages/PlayerPage";

export default function App() {
  return (
    <Routes>
      {/* 新しいメインページ */}
      <Route path="/" element={<HomePage />} />

      {/* ログイン画面（旧セッション入力画面から変更） */}
      <Route path="/login" element={<LoginPage />} />
      
      {/* 既存ページ */}
      <Route path="/session" element={<PairingPage />} />
      <Route path="/selectpage" element={<SelectPage />} />
      <Route path="/player" element={<PlayerPage />} />
    </Routes>
  );
}
 
