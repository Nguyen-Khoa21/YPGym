import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import * as Linking from 'expo-linking';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { Platform, Text, View } from 'react-native';

import { Action, Message, textStyles } from '@/components/ui';
import { apiRequest, errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';

type Provider = 'google' | 'facebook';
type ProviderStatus = { provider: Provider; enabled: boolean };

WebBrowser.maybeCompleteAuthSession();

export function SocialLoginActions() {
  const { completeOAuth } = useAuth();
  const [busy, setBusy] = useState<Provider | null>(null);
  const [error, setError] = useState('');
  const providers = useQuery({ queryKey: ['auth', 'providers'], queryFn: () => apiRequest<ProviderStatus[]>('/auth/providers') });
  async function start(provider: Provider) {
    setBusy(provider); setError('');
    try {
      const platform = Platform.OS === 'web' ? 'mobile_web' : 'mobile';
      const started = await apiRequest<{ authorization_url: string }>(`/auth/oauth/${provider}/start?platform=${platform}`);
      if (Platform.OS === 'web') { window.location.assign(started.authorization_url); return; }
      const result = await WebBrowser.openAuthSessionAsync(started.authorization_url, 'ypgym://oauth/callback');
      if (result.type !== 'success') { if (result.type !== 'cancel') setError('The provider browser could not complete sign-in.'); return; }
      const parsed = Linking.parse(result.url);
      const callbackError = typeof parsed.queryParams?.error === 'string' ? parsed.queryParams.error : null;
      const code = typeof parsed.queryParams?.code === 'string' ? parsed.queryParams.code : null;
      if (callbackError) throw new Error(callbackError.replaceAll('_', ' '));
      if (!code) throw new Error('The sign-in callback is invalid or expired.');
      await completeOAuth(provider, code);
      router.replace('/(member)/(tabs)/dashboard');
    } catch (caught) { setError(errorMessage(caught)); }
    finally { setBusy(null); }
  }
  return <View style={{ gap: 12, marginTop: 22 }}><Text style={[textStyles.eyebrow, { textAlign: 'center' }]}>Or continue with</Text>
    {(['google', 'facebook'] as const).map((provider) => { const enabled = providers.data?.find((item) => item.provider === provider)?.enabled ?? false; return <Action key={provider} label={busy === provider ? 'Opening…' : `Continue with ${provider === 'google' ? 'Google' : 'Facebook'}`} icon={<Ionicons accessible={false} name={provider === 'google' ? 'logo-google' : 'logo-facebook'} size={20} color={provider === 'google' ? '#4285F4' : '#1877F2'} />} onPress={() => void start(provider)} outline disabled={!enabled || busy !== null} />; })}
    {providers.data?.every((item) => !item.enabled) ? <Text style={[textStyles.muted, { textAlign: 'center' }]}>Social sign-in is awaiting provider configuration. Email sign-in remains available.</Text> : null}
    {error ? <Message title="Social sign-in failed" detail={error} tone="error" /> : null}
  </View>;
}
