import { Routes, Route, Outlet } from "react-router-dom";
import PairingPage from "./pages/PairingPage";
import PlayerPage from "./pages/PlayerPage";

function Layout() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-gray-100">
      <header className="sticky top-0 z-40 border-b border-black/5 bg-white/70 backdrop-blur-md dark:bg-gray-900/60">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-2 text-lg font-bold">
            <span>🎬</span><span>MyStream</span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<PairingPage />} />
        <Route path="/player" element={<PlayerPage />} />
      </Route>
    </Routes>
  );
}
