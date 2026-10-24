import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { ApiError, apiRequest, messageOf, SESSION_EXPIRED } from "../lib/api";
import { readToken, saveToken, tokenExpiry } from "../lib/session";
import type { TokenResponse, User } from "../lib/types";

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string;
  notice: string;
  signIn: (email: string, password: string) => Promise<void>;
  logout: () => void;
  retry: () => void;
}
const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState(readToken);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(token));
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [revision, setRevision] = useState(0);

  const clearSession = useCallback((message = "") => {
    saveToken(null);
    setToken(null);
    setUser(null);
    setLoading(false);
    setError("");
    setNotice(message);
  }, []);
  const logout = useCallback(() => clearSession(), [clearSession]);
  const retry = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    apiRequest<User>("/auth/me", { token, signal: controller.signal })
      .then((profile) => {
        if (!controller.signal.aborted) setUser(profile);
      })
      .catch((reason) => {
        if (
          !controller.signal.aborted &&
          !(reason instanceof ApiError && reason.status === 401)
        )
          setError(messageOf(reason));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [token, revision]);

  useEffect(() => {
    if (!token) return;
    const expire = () =>
      clearSession("Your session expired. Please sign in again.");
    const onUnauthorized = (event: Event) => {
      if ((event as CustomEvent).detail === token) expire();
    };
    window.addEventListener(SESSION_EXPIRED, onUnauthorized);
    const timer = window.setTimeout(
      expire,
      Math.max(0, (tokenExpiry(token) || 0) - Date.now()),
    );
    return () => {
      clearTimeout(timer);
      window.removeEventListener(SESSION_EXPIRED, onUnauthorized);
    };
  }, [token, clearSession]);

  async function signIn(email: string, password: string) {
    const result = await apiRequest<TokenResponse>("/auth/login", {
      method: "POST",
      body: { email: email.trim(), password },
    });
    if ((tokenExpiry(result.access_token) || 0) <= Date.now())
      throw new Error(
        "The server returned an expired session. Please sign in again.",
      );
    saveToken(result.access_token);
    setLoading(true);
    setNotice("");
    setError("");
    setToken(result.access_token);
  }

  return (
    <AuthContext.Provider
      value={{ user, token, loading, error, notice, signIn, logout, retry }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
