import { useState } from 'react';
import { router, type Href } from 'expo-router';
import { Text, View } from 'react-native';

import { Action, Brand, Card, Field, Heading, Message, Screen, textStyles } from '@/components/ui';
import { apiRequest, errorMessage } from '@/lib/api';
import type { RegisterResponse } from '@/lib/types';

type Errors = Partial<Record<'name' | 'email' | 'phone' | 'password' | 'confirmPassword', string>>;

export default function RegisterScreen() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [apiError, setApiError] = useState('');
  const [busy, setBusy] = useState(false);

  function change(field: keyof Errors, setter: (value: string) => void) {
    return (value: string) => { setter(value); if (errors[field]) setErrors((current) => ({ ...current, [field]: undefined })); };
  }

  async function submit() {
    const next: Errors = {
      ...(name.trim().length < 2 ? { name: 'Enter at least 2 characters.' } : {}),
      ...(!/^\S+@\S+\.\S+$/.test(email.trim()) ? { email: 'Enter a valid email address.' } : {}),
      ...(phone.trim().length < 7 ? { phone: 'Enter at least 7 characters.' } : {}),
      ...(password.length < 8 ? { password: 'Use at least 8 characters.' } : {}),
      ...(confirmPassword !== password ? { confirmPassword: 'Passwords do not match.' } : {}),
    };
    setErrors(next);
    if (Object.keys(next).length) return;
    setBusy(true); setApiError('');
    try {
      const response = await apiRequest<RegisterResponse>('/auth/register', undefined, { method: 'POST', body: { name: name.trim(), email: email.trim(), phone: phone.trim(), password } });
      router.replace(`/verify-email?email=${encodeURIComponent(response.user.email)}&message=${encodeURIComponent(response.message)}` as Href);
    } catch (error) { setApiError(errorMessage(error)); }
    finally { setBusy(false); }
  }

  return <Screen><Brand /><Heading eyebrow="New member" title="Create your YPGym account" detail="Register here, verify the one-time email link, then sign in to choose a membership." />
    <Card accent><Text style={textStyles.subheading}>One account, every visit</Text><Text style={textStyles.muted}>Your membership, scanner visits, classes and invoices stay connected to the same verified identity.</Text></Card>
    <View style={{ gap: 16 }}>
      <Field label="Full name" value={name} onChangeText={change('name', setName)} error={errors.name} autoComplete="name" />
      <Field label="Email address" value={email} onChangeText={change('email', setEmail)} error={errors.email} keyboardType="email-address" autoCapitalize="none" autoComplete="email" />
      <Field label="Phone number" value={phone} onChangeText={change('phone', setPhone)} error={errors.phone} keyboardType="phone-pad" autoComplete="tel" />
      <Field label="Password" value={password} onChangeText={change('password', setPassword)} error={errors.password} secureTextEntry autoComplete="new-password" />
      <Field label="Confirm password" value={confirmPassword} onChangeText={change('confirmPassword', setConfirmPassword)} error={errors.confirmPassword} secureTextEntry autoComplete="new-password" />
      {apiError ? <Message title="Registration failed" detail={apiError} tone="error" /> : null}
      <Action label={busy ? 'Creating account…' : 'Create account'} onPress={() => void submit()} disabled={busy} />
      <Action label="Back to sign in" onPress={() => router.replace('/login')} outline />
    </View>
  </Screen>;
}
