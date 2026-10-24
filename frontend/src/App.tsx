import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthProvider";
import { AuthPage } from "./pages/AuthPage";
import { InventoryPage } from "./pages/InventoryPage";
import { ErrorMessage, Loading } from "./components/Feedback";

export default function App() {
  const { user, loading, error, retry, logout } = useAuth();
  if (loading)
    return (
      <main className="grid min-h-screen place-items-center bg-stone-50">
        <Loading label="Checking your session…" />
      </main>
    );
  if (error)
    return (
      <main className="mx-auto max-w-md space-y-5 px-6 py-24">
        <h1 className="text-2xl font-semibold">
          Unable to restore your session
        </h1>
        <ErrorMessage message={error} />
        <div className="flex gap-3">
          <button className="btn-primary" onClick={retry}>
            Try again
          </button>
          <button className="btn-secondary" onClick={logout}>
            Return to sign in
          </button>
        </div>
      </main>
    );
  return (
    <Routes>
      <Route path="/login" element={<AuthPage key="login" />} />
      <Route path="/register" element={<AuthPage key="register" register />} />
      <Route
        path="/inventory"
        element={user ? <InventoryPage /> : <Navigate to="/login" replace />}
      />
      <Route
        path="*"
        element={<Navigate to={user ? "/inventory" : "/login"} replace />}
      />
    </Routes>
  );
}
