import { Redirect, Stack } from 'expo-router';

import { Busy, Message, Screen } from '@/components/ui';
import { useAuth } from '@/lib/auth';
import { mustChangePassword } from '@/lib/forcedPassword';
import { colors } from '@/lib/theme';

export default function MemberLayout() {
  const { ready, token, user, restoreError, retryRestore } = useAuth();
  if (!ready) return <Screen><Busy label="Restoring your session" /></Screen>;
  if (restoreError && !user) return <Screen><Message title="Connection unavailable" detail={restoreError} action="Retry" onAction={retryRestore} tone="error" /></Screen>;
  if (!token || !user) return <Redirect href="/login" />;
  if (mustChangePassword(user)) return <Redirect href="/change-password" />;
  return <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }} />;
}
