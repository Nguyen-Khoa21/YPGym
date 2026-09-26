import { useEffect, useState } from 'react';
import { router, useLocalSearchParams, type Href } from 'expo-router';

import { Brand, Busy, Message, Screen } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function OAuthCallback() {
  const params = useLocalSearchParams<{ provider?: string; code?: string; error?: string; linked?: string }>();
  const { completeOAuth } = useAuth();
  const [error, setError] = useState(() => params.error?.replaceAll('_', ' ') ?? (((params.provider !== 'google' && params.provider !== 'facebook') || !params.code) && !params.linked ? 'The sign-in callback is invalid or expired.' : ''));
  useEffect(() => {
    if (params.linked) { router.replace('/(member)/security' as Href); return; }
    if (params.error) return;
    if ((params.provider !== 'google' && params.provider !== 'facebook') || !params.code) return;
    void completeOAuth(params.provider, params.code).then(() => router.replace('/(member)/(tabs)/dashboard')).catch((caught) => setError(errorMessage(caught)));
  }, [completeOAuth, params.code, params.error, params.linked, params.provider]);
  return <Screen><Brand />{error ? <Message title="Sign-in could not be completed" detail={error} tone="error" /> : <Busy label="Completing secure sign-in" />}</Screen>;
}
