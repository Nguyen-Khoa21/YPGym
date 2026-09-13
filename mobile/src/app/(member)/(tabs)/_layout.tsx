import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';

import { colors } from '@/lib/theme';

const icons: Record<string, keyof typeof Ionicons.glyphMap> = { dashboard: 'grid-outline', qr: 'qr-code-outline', classes: 'calendar-outline', profile: 'person-outline' };

export default function MemberTabs() {
  return <Tabs screenOptions={({ route }) => ({
    headerShown: false,
    tabBarActiveTintColor: colors.lime,
    tabBarInactiveTintColor: colors.muted,
    tabBarStyle: { backgroundColor: '#222222', borderTopColor: colors.border, height: 68, paddingTop: 6 },
    tabBarLabelStyle: { fontSize: 11, fontWeight: '700', paddingBottom: 4 },
    tabBarIcon: ({ color, size }) => <Ionicons name={icons[route.name] ?? 'ellipse-outline'} size={size} color={color} />,
  })}>
    <Tabs.Screen name="dashboard" options={{ title: 'Dashboard' }} />
    <Tabs.Screen name="qr" options={{ title: 'Check-in' }} />
    <Tabs.Screen name="classes" options={{ title: 'Classes' }} />
    <Tabs.Screen name="profile" options={{ title: 'Profile' }} />
  </Tabs>;
}
