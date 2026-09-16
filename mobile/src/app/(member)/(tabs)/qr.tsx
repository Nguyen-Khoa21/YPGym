import { useCallback, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import QRCode from 'react-native-qrcode-svg';
import { AppState, Text, View, useWindowDimensions } from 'react-native';

import { Action, Brand, Busy, Card, Heading, Message, Pill, Screen, textStyles } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { mayShowQr, qrSecondsLeft } from '@/lib/qr';
import type { Dashboard, QrToken } from '@/lib/types';

export default function QrScreen() {
  const { request, user } = useAuth();
  const { width } = useWindowDimensions();
  const [now, setNow] = useState(Date.now);
  const [foregroundReady, setForegroundReady] = useState(true);
  const access = useQuery({ queryKey: ['dashboard', user?.id], queryFn: ({ signal }) => request<Dashboard>('/dashboard/me', { signal }), refetchInterval: 30_000 });
  const eligible = access.data?.qr_access.eligible === true;
  const qr = useQuery({ queryKey: ['qr', user?.id], queryFn: ({ signal }) => request<QrToken>('/attendance/qr-token/me', { signal }), enabled: eligible,
    retry: false, refetchInterval: (query) => query.state.data ? Math.max(1000, new Date(query.state.data.expires_at).getTime() - Date.now() - 5000) : false });
  const refetchQr = qr.refetch;
  const refreshQr = useCallback(async () => {
    const result = await refetchQr();
    setForegroundReady(AppState.currentState === 'active' && result.isSuccess);
  }, [refetchQr]);

  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  useEffect(() => {
    const subscription = AppState.addEventListener('change', (state) => {
      setForegroundReady(false);
      if (state === 'active' && eligible) void refreshQr();
    });
    return () => subscription.remove();
  }, [eligible, refreshQr]);

  const seconds = qrSecondsLeft(qr.data?.expires_at, now);
  const showCode = mayShowQr(eligible, foregroundReady, qr.isError, seconds, Boolean(qr.data?.token));
  return <Screen onRefresh={() => { void access.refetch(); if (eligible) void refreshQr(); }} refreshing={access.isRefetching || qr.isRefetching}>
    <Brand /><Heading title={user?.name ?? 'Check-in pass'} detail={`${user?.tier.toUpperCase() ?? 'MEMBER'} · ID ${user?.id.slice(0, 8) ?? ''}`} />
    {access.isLoading ? <Busy label="Checking membership access" /> : null}
    {access.isError ? <Message title="Access unavailable" detail={errorMessage(access.error)} action="Retry" onAction={() => void access.refetch()} /> : null}
    {access.data && !eligible ? <Message title="QR access restricted" detail={access.data.qr_access.reason ?? access.data.membership?.message ?? 'An active membership is required.'} action="View plans" onAction={() => router.push('/(member)/renew')} /> : null}
    {eligible ? <Card accent><Text style={[textStyles.muted, { textAlign: 'center' }]}>Scan this code at the gym entrance</Text><Pill label={showCode ? 'Live entry code' : 'Checking code'} centered />
      {qr.isLoading ? <Busy label="Issuing your rotating pass" /> : null}
      {qr.isError ? <Message title="Code unavailable" detail={errorMessage(qr.error)} action="Try again" onAction={() => void refreshQr()} /> : null}
      {showCode && qr.data ? <View style={{ alignItems: 'center', paddingVertical: 18, gap: 17 }}><View style={{ backgroundColor: '#ffffff', padding: 16, borderRadius: 15 }}><QRCode value={qr.data.token} size={Math.min(width - 102, 252)} backgroundColor="#ffffff" color="#171717" /></View><Text style={textStyles.lime}>Refreshes in {seconds}s</Text></View> : qr.data && !qr.isError ? <Message title="Pass refreshing" detail="A fresh server-issued code is required before check-in." action="Refresh now" onAction={() => void refreshQr()} /> : null}
      <Text style={[textStyles.muted, { textAlign: 'center' }]}>Codes expire and are superseded on refresh. Screenshots do not grant access.</Text>
    </Card> : null}
    <Action label="View attendance history" outline onPress={() => router.push('/(member)/attendance')} />
  </Screen>;
}
