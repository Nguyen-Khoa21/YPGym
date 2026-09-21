import { useState } from 'react';
import { router, useLocalSearchParams } from 'expo-router';
import { View } from 'react-native';

import { Action, Brand, Field, Heading, Message, Screen } from '@/components/ui';
import { apiRequest, errorMessage } from '@/lib/api';
import type { VerifyEmailResponse } from '@/lib/types';

function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] ?? '' : value ?? ''; }

export default function VerifyEmailScreen() {
  const params = useLocalSearchParams<{ token?: string | string[]; email?: string | string[]; message?: string | string[] }>();
  const [token, setToken] = useState(first(params.token));
  const [result, setResult] = useState('');
  const [failure, setFailure] = useState('');
  const [busy, setBusy] = useState(false);

  async function verify() {
    if (token.trim().length < 16) { setFailure('Open the one-time link from your email, or paste its token here.'); return; }
    setBusy(true); setFailure('');
    try {
      const response = await apiRequest<VerifyEmailResponse>(`/auth/verify-email?token=${encodeURIComponent(token.trim())}`);
      setResult(response.message);
    } catch (error) { setFailure(errorMessage(error)); }
    finally { setBusy(false); }
  }

  return <Screen><Brand /><Heading eyebrow="Email verification" title="Verify your account" detail={first(params.email) ? `We sent a one-time verification link for ${first(params.email)}.` : 'Open the one-time link from your registration email.'} />
    {first(params.message) ? <Message title="Account created" detail={first(params.message)} tone="success" /> : null}
    {result ? <Message title="Email verified" detail={result} tone="success" /> : <View style={{ gap: 16 }}><Field label="Verification token" value={token} onChangeText={(value) => { setToken(value); setFailure(''); }} error={failure || undefined} autoCapitalize="none" autoCorrect={false} /><Action label={busy ? 'Verifying…' : 'Verify email'} onPress={() => void verify()} disabled={busy} /></View>}
    <Action label={result ? 'Continue to sign in' : 'Back to sign in'} onPress={() => router.replace('/login')} outline />
  </Screen>;
}
