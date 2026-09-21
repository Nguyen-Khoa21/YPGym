import { createContext, useCallback, useContext, useEffect, useRef, useState, type PropsWithChildren } from 'react';
import * as SecureStore from 'expo-secure-store';
import { router } from 'expo-router';
import { Platform } from 'react-native';

import { apiRequest, ApiError, errorMessage } from '@/lib/api';
import { clearMemberQueryData } from '@/lib/query';
import { endMemberSession, restoreMemberSession } from '@/lib/session';
import type { LoginResponse, User } from '@/lib/types';

const TOKEN_KEY = 'ypgym_member_token';
async function readToken() {
  if (Platform.OS !== 'web') return SecureStore.getItemAsync(TOKEN_KEY);
  return window.sessionStorage.getItem(TOKEN_KEY) ?? window.localStorage.getItem(TOKEN_KEY);
}
async function saveToken(value: string) {
  if (Platform.OS !== 'web') return SecureStore.setItemAsync(TOKEN_KEY, value);
  window.localStorage.removeItem(TOKEN_KEY);
  window.sessionStorage.setItem(TOKEN_KEY, value);
}
async function deleteToken() {
  if (Platform.OS !== 'web') return SecureStore.deleteItemAsync(TOKEN_KEY);
  window.sessionStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(TOKEN_KEY);
}

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
    await endMemberSession({
      clearMemory: () => {
        currentToken.current = null;
        setToken(null);
        setUser(null);
        setRestoreError(null);
      },
      clearQueries: clearMemberQueryData,
      clearStoredToken: deleteToken,
      resetNavigation: () => router.replace('/login'),
    });
  }, []);

  useEffect(() => {
    let mounted = true;
    async function restore() {
      const result = await restoreMemberSession({
        readToken,
        loadUser: (stored) => apiRequest<User>('/auth/me', stored),
        discardStoredSession: async () => { clearMemberQueryData(); await deleteToken(); },
        isUnauthorized: (error) => error instanceof ApiError && error.status === 401,
      });
      if (!mounted) return;
      if (result.kind === 'authenticated') {
        currentToken.current = result.token;
        setToken(result.token);
        setUser(result.user);
        setRestoreError(null);
      } else if (result.kind === 'retry') {
        currentToken.current = result.token;
        setToken(result.token);
        setUser(null);
        setRestoreError(errorMessage(result.error));
      } else {
        currentToken.current = null;
        setToken(null);
        setUser(null);
        setRestoreError(null);
      }
      setReady(true);
    }
    void restore().catch((error) => {
      if (!mounted) return;
      setRestoreError(errorMessage(error));
      setReady(true);
    });
    return () => { mounted = false; };
  }, [restoreAttempt]);

  const login = useCallback(async (email: string, password: string) => {
    const result = await apiRequest<LoginResponse>('/auth/login', undefined, { method: 'POST', body: { email, password } });
    if (result.user.role !== 'member') throw new ApiError('This app is for members. Use the web workspace for your role.', 403, 'PERMISSION_DENIED');
    await saveToken(result.access_token);
    clearMemberQueryData();
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
