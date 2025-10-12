import { Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import PairingPage from "./pages/PairingPage";
import SelectPage from "./pages/SelectPage";
import PlayerPage from "./pages/PlayerPage";

export default function App() {
  return (
    <Routes>
      {/* 新しいメインページ */}
      <Route path="/" element={<HomePage />} />

      {/* 既存ページ */}
      <Route path="/session" element={<PairingPage />} />
      <Route path="/selectpage" element={<SelectPage />} />
      <Route path="/player" element={<PlayerPage />} />
    </Routes>
  );
}
