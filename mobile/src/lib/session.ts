export type SessionUser = { role: string };

export type RestoreResult<T extends SessionUser> =
  | { kind: 'anonymous' }
  | { kind: 'authenticated'; token: string; user: T }
  | { kind: 'retry'; token: string | null; error: unknown };

export async function restoreMemberSession<T extends SessionUser>({
  readToken,
  loadUser,
  discardStoredSession,
  isUnauthorized,
}: {
  readToken: () => Promise<string | null>;
  loadUser: (token: string) => Promise<T>;
  discardStoredSession: () => Promise<void>;
  isUnauthorized: (error: unknown) => boolean;
}): Promise<RestoreResult<T>> {
  let stored: string | null;
  try {
    stored = await readToken();
  } catch (error) {
    return { kind: 'retry', token: null, error };
  }
  if (!stored) return { kind: 'anonymous' };

  try {
    const user = await loadUser(stored);
    if (user.role !== 'member') {
      await discardStoredSession();
      return { kind: 'anonymous' };
    }
    return { kind: 'authenticated', token: stored, user };
  } catch (error) {
    if (isUnauthorized(error)) {
      await discardStoredSession();
      return { kind: 'anonymous' };
    }
    return { kind: 'retry', token: stored, error };
  }
}

export async function endMemberSession({
  clearMemory,
  clearQueries,
  clearStoredToken,
  resetNavigation,
}: {
  clearMemory: () => void;
  clearQueries: () => void;
  clearStoredToken: () => Promise<void>;
  resetNavigation: () => void;
}) {
  clearMemory();
  clearQueries();
  try {
    await clearStoredToken();
  } finally {
    resetNavigation();
  }
}
