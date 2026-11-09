import { useState } from 'react';
import { Redirect } from 'expo-router';
import { View } from 'react-native';

import { Action, Brand, Field, Heading, Message, Screen } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { mustChangePassword, validatePasswordChange } from '@/lib/forcedPassword';
import type { User } from '@/lib/types';

export default function ChangePassword() {
  const { request, refreshUser, user, token } = useAuth();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [errors, setErrors] = useState<{ current?: string; next?: string; confirm?: string }>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  if (!token || !user) return <Redirect href="/login" />;
  if (!mustChangePassword(user)) return <Redirect href="/(member)/(tabs)/dashboard" />;
  async function submit() {
    const found = validatePasswordChange({ current, next, confirm });
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true); setError('');
    try {
      await request<User>('/users/me', { method: 'PATCH', body: { current_password: current, new_password: next } });
      await refreshUser();
    } catch (caught) { setError(errorMessage(caught)); }
    finally { setBusy(false); }
  }
  return <Screen><Brand /><Heading eyebrow="Account security" title="Set your private password." detail="The gym gave you a temporary password. Replace it before you continue." />
    <View style={{ gap: 16, marginTop: 20 }}>
      <Field label="Temporary password" value={current} onChangeText={setCurrent} error={errors.current} secureTextEntry autoComplete="current-password" />
      <Field label="New password" value={next} onChangeText={setNext} error={errors.next} secureTextEntry autoComplete="new-password" />
      <Field label="Confirm new password" value={confirm} onChangeText={setConfirm} error={errors.confirm} secureTextEntry autoComplete="new-password" />
      {error ? <Message title="Password not changed" detail={error} tone="error" /> : null}
      <Action label={busy ? 'Saving…' : 'Set password and continue'} onPress={() => void submit()} disabled={busy} />
    </View></Screen>;
}
