import { useMutation, useQuery } from '@tanstack/react-query';
import * as WebBrowser from 'expo-web-browser';
import { Text, View } from 'react-native';

import { Action, Brand, Busy, Card, Message, PageTop, Screen, textStyles } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { queryClient } from '@/lib/query';

type Provider = 'google' | 'facebook';
type Identities = { password_enabled: boolean; identities: { provider: Provider; email: string | null; email_verified: boolean; last_login_at: string | null }[] };

export default function SecurityScreen() {
  const { request } = useAuth();
  const identities = useQuery({ queryKey: ['account', 'identities'], queryFn: () => request<Identities>('/account/identities') });
  const unlink = useMutation({ mutationFn: (provider: Provider) => request<Identities>(`/account/identities/${provider}`, { method: 'DELETE' }), onSuccess: (data) => queryClient.setQueryData(['account', 'identities'], data) });
  async function link(provider: Provider) {
    const started = await request<{ authorization_url: string }>(`/account/identities/${provider}/link/start?platform=mobile`, { method: 'POST' });
    const result = await WebBrowser.openAuthSessionAsync(started.authorization_url, 'ypgym://oauth/callback');
    if (result.type === 'success') await identities.refetch();
  }
  return <Screen><Brand /><PageTop title="Sign-in methods" fallback="/(member)/(tabs)/profile" /><Card accent><Text style={textStyles.subheading}>Account linking</Text><Text style={textStyles.muted}>Matching email alone never links accounts. Changes require a recent YPGym sign-in.</Text></Card>
    {identities.isLoading ? <Busy label="Loading sign-in methods" /> : null}{identities.isError ? <Message title="Security settings unavailable" detail={errorMessage(identities.error)} tone="error" /> : null}
    {identities.data ? <View style={{ gap: 12 }}><Card><Text style={textStyles.body}>Email and password</Text><Text style={textStyles.muted}>{identities.data.password_enabled ? 'Available' : 'No password is set for this provider-created account.'}</Text></Card>{(['google', 'facebook'] as const).map((provider) => { const linked = identities.data?.identities.find((item) => item.provider === provider); return <Card key={provider}><Text style={textStyles.subheading}>{provider === 'google' ? 'Google' : 'Facebook'}</Text><Text style={textStyles.muted}>{linked ? `Connected${linked.email ? ` · ${linked.email}` : ''}` : 'Not connected'}</Text>{linked ? <Action label="Disconnect" onPress={() => unlink.mutate(provider)} outline disabled={unlink.isPending} /> : <Action label="Connect" onPress={() => void link(provider)} outline />}</Card>; })}{unlink.isError ? <Message title="Provider could not be disconnected" detail={errorMessage(unlink.error)} tone="error" /> : null}</View> : null}
  </Screen>;
}
