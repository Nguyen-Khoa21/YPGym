import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

import { apiRequest } from "@/lib/apiClient";
import { queryClient } from "@/lib/queryClient";
import type { LoginResponse, User } from "@/types/api";

const TOKEN_KEY = "ypgym_access_token";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  completeOAuth: (provider: "google" | "facebook", code: string) => Promise<User>;
  completeOAuthLink: (path: "/auth/oauth/link/password" | "/auth/oauth/link/email/confirm", body: unknown) => Promise<User>;
  logout: () => void;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(() =>
    window.localStorage.getItem(TOKEN_KEY),
  );
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(token));

  const clearAuth = useCallback(() => {
    queryClient.clear();
    window.localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const currentUser = await apiRequest<User>("/auth/me", { token });
      setUser(currentUser);
    } catch {
      clearAuth();
    } finally {
      setIsLoading(false);
    }
  }, [clearAuth, token]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshUser();
  }, [refreshUser]);

  useEffect(() => {
    // API requests notify here so expired sessions are cleared consistently.
    window.addEventListener("ypgym:unauthorized", clearAuth);
    return () => window.removeEventListener("ypgym:unauthorized", clearAuth);
  }, [clearAuth]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await apiRequest<LoginResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
    });
    queryClient.clear();
    window.localStorage.setItem(TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    setUser(response.user);
    return response.user;
  }, []);

  const acceptLogin = useCallback((response: LoginResponse) => {
    queryClient.clear();
    window.localStorage.setItem(TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    setUser(response.user);
    return response.user;
  }, []);

  const completeOAuth = useCallback(async (provider: "google" | "facebook", code: string) => {
    const response = await apiRequest<LoginResponse>(`/auth/oauth/${provider}/exchange`, {
      method: "POST",
      body: { code },
    });
    return acceptLogin(response);
  }, [acceptLogin]);

  const completeOAuthLink = useCallback(async (
    path: "/auth/oauth/link/password" | "/auth/oauth/link/email/confirm",
    body: unknown,
  ) => acceptLogin(await apiRequest<LoginResponse>(path, { method: "POST", body })), [acceptLogin]);

  const value = useMemo(
    () => ({
      token,
      user,
      isLoading,
      login,
      completeOAuth,
      completeOAuthLink,
      logout: clearAuth,
      refreshUser,
    }),
    [clearAuth, completeOAuth, completeOAuthLink, isLoading, login, refreshUser, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
