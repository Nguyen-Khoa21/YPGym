import { useEffect, useState } from 'react';
import { router, useLocalSearchParams } from 'expo-router';
import { View } from 'react-native';

import { Action, Brand, Field, Heading, Message, Screen } from '@/components/ui';
import { apiRequest, errorMessage } from '@/lib/api';
import type { VerifyEmailResponse } from '@/lib/types';

const RESEND_COOLDOWN_SECONDS = 60;

function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] ?? '' : value ?? ''; }

export default function VerifyEmailScreen() {
  const params = useLocalSearchParams<{ token?: string | string[]; email?: string | string[]; message?: string | string[] }>();
  const [email, setEmail] = useState(first(params.email));
  const [code, setCode] = useState('');
  const [result, setResult] = useState('');
  const [notice, setNotice] = useState('');
  const [failure, setFailure] = useState('');
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const emailValid = /^\S+@\S+\.\S+$/.test(email.trim());

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((value) => value - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  // Older emails still carry a one-time token; it keeps working when a link opens this screen.
  const linkToken = first(params.token);
  useEffect(() => {
    if (linkToken.length < 16) return;
    let active = true;
    setBusy(true);
    apiRequest<VerifyEmailResponse>(`/auth/verify-email?token=${encodeURIComponent(linkToken)}`)
      .then((response) => { if (active) setResult(response.message); })
      .catch((error) => { if (active) setFailure(errorMessage(error)); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [linkToken]);

  async function verify() {
    if (!emailValid) { setFailure('Enter the email you registered with.'); return; }
    if (!/^\d{6}$/.test(code)) { setFailure('Enter all 6 digits from your email.'); return; }
    setBusy(true); setFailure(''); setNotice('');
    try {
      const response = await apiRequest<VerifyEmailResponse>('/auth/verify-email/code', null, { method: 'POST', body: { email: email.trim(), code } });
      setResult(response.message);
    } catch (error) { setFailure(errorMessage(error)); }
    finally { setBusy(false); }
  }

  async function resend() {
    if (!emailValid) { setFailure('Enter the email you registered with.'); return; }
    setBusy(true); setFailure(''); setNotice('');
    try {
      const response = await apiRequest<{ message: string }>('/auth/verify-email/resend', null, { method: 'POST', body: { email: email.trim() } });
      setNotice(response.message); setCode(''); setCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (error) { setFailure(errorMessage(error)); }
    finally { setBusy(false); }
  }

  return <Screen><Brand /><Heading eyebrow="Email verification" title="Verify your account" detail="Enter the 6-digit code we emailed you. It expires after a few minutes." />
    {first(params.message) ? <Message title="Account created" detail={first(params.message)} tone="success" /> : null}
    {notice ? <Message title="Code sent" detail={notice} tone="success" /> : null}
    {result ? <Message title="Email verified" detail={result} tone="success" /> : <View style={{ gap: 16 }}>
      <Field label="Email address" value={email} onChangeText={(value) => { setEmail(value); setFailure(''); }} autoCapitalize="none" autoCorrect={false} keyboardType="email-address" autoComplete="email" />
      <Field label="6-digit code" value={code} onChangeText={(value) => { setCode(value.replace(/\D/g, '').slice(0, 6)); setFailure(''); }} error={failure || undefined} keyboardType="number-pad" textContentType="oneTimeCode" autoComplete="sms-otp" maxLength={6} autoCorrect={false} />
      <Action label={busy ? 'Working…' : 'Verify email'} onPress={() => void verify()} disabled={busy} />
      <Action label={cooldown > 0 ? `Send a new code in ${cooldown}s` : 'Send a new code'} onPress={() => void resend()} disabled={busy || cooldown > 0} outline />
    </View>}
    <Action label={result ? 'Continue to sign in' : 'Back to sign in'} onPress={() => router.replace('/login')} outline />
  </Screen>;
}
