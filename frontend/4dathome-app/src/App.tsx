import { Routes, Route, Navigate } from "react-router-dom";
import PairingPage from "./pages/PairingPage";
import SelectPage from "./pages/SelectPage";
import PlayerPage from "./pages/PlayerPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<PairingPage />} />
      <Route path="/selectpage" element={<SelectPage />} />
      <Route path="/player" element={<PlayerPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
