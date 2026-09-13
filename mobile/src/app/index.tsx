import { Redirect } from 'expo-router';

import { Busy, Message, Screen } from '@/components/ui';
import { useAuth } from '@/lib/auth';

export default function Start() {
  const { ready, token, user, restoreError, retryRestore } = useAuth();
  if (!ready) return <Screen><Busy label="Restoring your session" /></Screen>;
  if (restoreError && token && !user) return <Screen><Message title="Connection unavailable" detail={restoreError} action="Retry" onAction={retryRestore} /></Screen>;
  return <Redirect href={token && user ? '/(member)/(tabs)/dashboard' : '/login'} />;
}
