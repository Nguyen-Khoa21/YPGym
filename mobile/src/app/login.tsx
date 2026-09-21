import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Redirect, router } from 'expo-router';
import { Text, View } from 'react-native';

import { Action, Brand, Card, Field, Heading, Message, Screen, textStyles } from '@/components/ui';
import { apiRequest, errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors } from '@/lib/theme';

export default function Login() {
  const { login, token, user } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const health = useQuery({ queryKey: ['health'], queryFn: () => apiRequest<{ status: string }>('/health'), retry: false });
  if (token && user) return <Redirect href="/(member)/(tabs)/dashboard" />;
  async function submit() {
    const nextErrors = { ...(!email.trim() ? { email: 'Enter your email address.' } : {}), ...(!password ? { password: 'Enter your password.' } : {}) };
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    setBusy(true); setError('');
    try { await login(email.trim(), password); router.replace('/(member)/(tabs)/dashboard'); }
    catch (caught) { setError(errorMessage(caught)); }
    finally { setBusy(false); }
  }
  return <Screen><Brand /><Heading eyebrow="Member training hub" title="Back to your training." detail="Sign in with your verified YPGym member account." />
    <Card accent><Text style={textStyles.subheading}>Welcome back</Text><Text style={textStyles.muted}>Your membership, check-in code, classes and profile are connected to the gym.</Text></Card>
    <View style={{ gap: 16, marginTop: 20 }}><Field label="Email address" value={email} onChangeText={(value) => { setEmail(value); if (fieldErrors.email) setFieldErrors((current) => ({ ...current, email: undefined })); }} error={fieldErrors.email} keyboardType="email-address" autoCapitalize="none" autoComplete="email" /><Field label="Password" value={password} onChangeText={(value) => { setPassword(value); if (fieldErrors.password) setFieldErrors((current) => ({ ...current, password: undefined })); }} error={fieldErrors.password} secureTextEntry autoComplete="current-password" />
      {error ? <Message title="Sign-in failed" detail={error} tone="error" /> : null}<Action label={busy ? 'Signing in…' : 'Sign in'} onPress={() => void submit()} disabled={busy} /></View>
    <Text style={{ color: health.isSuccess ? colors.primary : colors.muted, marginTop: 22, textAlign: 'center' }}>{health.isLoading ? 'Checking API…' : health.isSuccess ? 'Gym API online' : `Gym API unavailable: ${errorMessage(health.error)}`}</Text>
  </Screen>;
}
