import { Navigate } from "react-router-dom";

export default function ProtectedRoute({ children }: { children: JSX.Element }) {
  const isAuthed = ((): boolean => {
    try { return sessionStorage.getItem("auth") === "1"; } catch { return false; }
  })();
  if (!isAuthed) return <Navigate to="/login" replace />;
  return children;
}
