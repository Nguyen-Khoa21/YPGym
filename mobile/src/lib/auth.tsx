import { createContext, useCallback, useContext, useEffect, useRef, useState, type PropsWithChildren } from 'react';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

import { apiRequest, ApiError, errorMessage } from '@/lib/api';
import { queryClient } from '@/lib/query';
import type { LoginResponse, User } from '@/lib/types';

const TOKEN_KEY = 'ypgym_member_token';
const readToken = () => Platform.OS === 'web' ? Promise.resolve(window.sessionStorage.getItem(TOKEN_KEY)) : SecureStore.getItemAsync(TOKEN_KEY);
const saveToken = (value: string) => Platform.OS === 'web' ? Promise.resolve(window.sessionStorage.setItem(TOKEN_KEY, value)) : SecureStore.setItemAsync(TOKEN_KEY, value);
const deleteToken = () => Platform.OS === 'web' ? Promise.resolve(window.sessionStorage.removeItem(TOKEN_KEY)) : SecureStore.deleteItemAsync(TOKEN_KEY);

type Options = { method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'; body?: unknown; signal?: AbortSignal };
type Session = {
  ready: boolean; token: string | null; user: User | null; restoreError: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  retryRestore: () => void;
  refreshUser: () => Promise<void>;
  request: <T>(path: string, options?: Options) => Promise<T>;
};
const Context = createContext<Session | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [ready, setReady] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const currentToken = useRef<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [restoreAttempt, setRestoreAttempt] = useState(0);

  const logout = useCallback(async (expectedToken?: string) => {
    if (expectedToken && expectedToken !== currentToken.current) return;
    currentToken.current = null;
    queryClient.clear();
    await deleteToken();
    setToken(null);
    setUser(null);
    setRestoreError(null);
  }, []);

  useEffect(() => {
    let mounted = true;
    async function restore() {
      try {
        const stored = await readToken();
        if (!mounted || !stored) return;
        currentToken.current = stored;
        setToken(stored);
        const profile = await apiRequest<User>('/auth/me', stored);
        if (!mounted || currentToken.current !== stored) return;
        if (profile.role !== 'member') { await logout(stored); return; }
        setUser(profile);
        setRestoreError(null);
      } catch (error) {
        if (!mounted) return;
        if (error instanceof ApiError && error.status === 401) await logout(currentToken.current ?? undefined);
        else setRestoreError(errorMessage(error));
      } finally { if (mounted) setReady(true); }
    }
    void restore();
    return () => { mounted = false; };
  }, [logout, restoreAttempt]);

  const login = useCallback(async (email: string, password: string) => {
    const result = await apiRequest<LoginResponse>('/auth/login', undefined, { method: 'POST', body: { email, password } });
    if (result.user.role !== 'member') throw new ApiError('This app is for members. Use the web workspace for your role.', 403, 'PERMISSION_DENIED');
    await saveToken(result.access_token);
    queryClient.clear();
    currentToken.current = result.access_token;
    setToken(result.access_token);
    setUser(result.user);
    setRestoreError(null);
  }, []);

  const request = useCallback(async <T,>(path: string, options?: Options) => {
    try { return await apiRequest<T>(path, token, options); }
    catch (error) {
      if (error instanceof ApiError && error.status === 401 && token) await logout(token);
      throw error;
    }
  }, [logout, token]);

  const refreshUser = useCallback(async () => {
    if (!token) return;
    const refreshed = await request<User>('/auth/me');
    setUser(refreshed);
  }, [request, token]);

  return <Context.Provider value={{ ready, token, user, restoreError, login, logout: () => logout(), retryRestore: () => setRestoreAttempt((n) => n + 1), refreshUser, request }}>{children}</Context.Provider>;
}

export function useAuth() {
  const context = useContext(Context);
  if (!context) throw new Error('AuthProvider is required');
  return context;
}
