import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Alert, Text, View } from 'react-native';

import { Action, Busy, Field, Heading, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { queryClient } from '@/lib/query';
import type { User } from '@/lib/types';

export default function ProfileEditScreen() {
  const { request, user, refreshUser } = useAuth();
  const profile = useQuery({ queryKey: ['profile', user?.id], queryFn: ({ signal }) => request<User>('/users/me', { signal }) });
  const [nameInput, setNameInput] = useState<string | null>(null); const [phoneInput, setPhoneInput] = useState<string | null>(null);
  const name = nameInput ?? profile.data?.name ?? ''; const phone = phoneInput ?? profile.data?.phone ?? '';
  const [currentPassword, setCurrentPassword] = useState(''); const [newPassword, setNewPassword] = useState('');
  const [validation, setValidation] = useState<{ name?: string; phone?: string; currentPassword?: string; newPassword?: string }>({});
  const save = useMutation({ mutationFn: () => request<User>('/users/me', { method: 'PATCH', body: { name: name.trim(), phone: phone.trim(), ...(newPassword ? { current_password: currentPassword, new_password: newPassword } : {}) } }),
    onSuccess: async (updated) => { queryClient.setQueryData(['profile', user?.id], updated); setNameInput(null); setPhoneInput(null); setCurrentPassword(''); setNewPassword(''); await refreshUser(); Alert.alert('Profile updated'); },
    onError: (error) => Alert.alert('Could not update profile', errorMessage(error)) });
  function submit() {
    const nextValidation = {
      ...(name.trim().length < 2 ? { name: 'Enter at least 2 characters.' } : {}),
      ...(phone.trim().length < 7 ? { phone: 'Enter at least 7 characters.' } : {}),
      ...(newPassword && !currentPassword ? { currentPassword: 'Enter your current password to authorize this change.' } : {}),
      ...(newPassword && newPassword.length < 8 ? { newPassword: 'Use at least 8 characters.' } : {}),
    };
    setValidation(nextValidation);
    if (Object.keys(nextValidation).length) return;
    save.mutate();
  }
  return <Screen><PageTop title="Personal Information" fallback="/(member)/(tabs)/profile" /><Heading title="Your details" detail="Name and phone are editable. Email changes require a separate verification flow." />
    {profile.isLoading ? <Busy label="Loading profile" /> : null}{profile.isError ? <Message title="Profile unavailable" detail={errorMessage(profile.error)} action="Retry" onAction={() => void profile.refetch()} tone="error" /> : null}
    {profile.data ? <View style={{ gap: 17 }}><Field label="Full name" value={name} onChangeText={(value) => { setNameInput(value); if (validation.name) setValidation((current) => ({ ...current, name: undefined })); }} error={validation.name} autoComplete="name" /><Field label="Phone number" value={phone} onChangeText={(value) => { setPhoneInput(value); if (validation.phone) setValidation((current) => ({ ...current, phone: undefined })); }} error={validation.phone} keyboardType="phone-pad" autoComplete="tel" /><Text style={textStyles.muted}>Verified email: {profile.data.email}</Text>
      <Text style={[textStyles.subheading, { marginTop: 12 }]}>Account security</Text><Text style={textStyles.muted}>Leave password fields empty to keep your current password.</Text><Field label="Current password" value={currentPassword} onChangeText={(value) => { setCurrentPassword(value); if (validation.currentPassword) setValidation((current) => ({ ...current, currentPassword: undefined })); }} error={validation.currentPassword} secureTextEntry autoComplete="current-password" /><Field label="New password" value={newPassword} onChangeText={(value) => { setNewPassword(value); if (validation.newPassword) setValidation((current) => ({ ...current, newPassword: undefined })); }} error={validation.newPassword} secureTextEntry autoComplete="new-password" />
      <Action label={save.isPending ? 'Saving…' : 'Save profile'} disabled={save.isPending} onPress={submit} /></View> : null}
  </Screen>;
}
