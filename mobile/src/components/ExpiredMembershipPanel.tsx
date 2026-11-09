import { router } from 'expo-router';
import { Text, View } from 'react-native';

import { Action, Card, textStyles } from '@/components/ui';
import { formatDate } from '@/lib/api';
import { isExpiredStatus, renewScreenParams } from '@/lib/expired';

type PanelMembership = { status: string; home_gym_name: string; expiry_date: string };

export function ExpiredMembershipPanel({ membership }: { membership: PanelMembership | null | undefined }) {
  if (!membership || !isExpiredStatus(membership.status)) return null;
  return <Card accent>
    <Text style={textStyles.eyebrow}>Membership expired</Text>
    <Text style={textStyles.subheading}>Your membership at {membership.home_gym_name} expired on {formatDate(membership.expiry_date)}.</Text>
    <Text style={textStyles.muted}>Renew to use your check-in code again, or switch to another location. Your gym only changes after the payment is confirmed.</Text>
    <View style={{ gap: 10, marginTop: 12 }}>
      <Action label={`Renew at ${membership.home_gym_name}`} onPress={() => router.push({ pathname: '/(member)/renew', params: renewScreenParams('renew') })} />
      <Action label="Change location" outline onPress={() => router.push({ pathname: '/(member)/renew', params: renewScreenParams('change') })} />
    </View>
  </Card>;
}
