import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';

import { colors } from '@/lib/theme';

const icons: Record<string, { active: keyof typeof Ionicons.glyphMap; inactive: keyof typeof Ionicons.glyphMap }> = {
  dashboard: { active: 'grid', inactive: 'grid-outline' },
  qr: { active: 'qr-code', inactive: 'qr-code-outline' },
  classes: { active: 'calendar', inactive: 'calendar-outline' },
  train: { active: 'barbell', inactive: 'barbell-outline' },
  profile: { active: 'person', inactive: 'person-outline' },
};

export default function MemberTabs() {
  return <Tabs screenOptions={({ route }) => ({
    headerShown: false,
    tabBarActiveTintColor: colors.primary,
    tabBarInactiveTintColor: colors.muted,
    tabBarStyle: { backgroundColor: colors.white, borderTopColor: colors.border, height: 72, paddingTop: 7 },
    tabBarItemStyle: { minHeight: 48 },
    tabBarLabelStyle: { fontSize: 11, fontWeight: '800', paddingBottom: 5 },
    tabBarIcon: ({ color, size, focused }) => {
      const icon = icons[route.name];
      return <Ionicons name={icon ? (focused ? icon.active : icon.inactive) : 'ellipse-outline'} size={size} color={color} />;
    },
  })}>
    <Tabs.Screen name="dashboard" options={{ title: 'Dashboard' }} />
    <Tabs.Screen name="qr" options={{ title: 'Check-in' }} />
    <Tabs.Screen name="classes" options={{ title: 'Classes' }} />
    <Tabs.Screen name="train" options={{ title: 'YPTrain' }} />
    <Tabs.Screen name="profile" options={{ title: 'Profile' }} />
  </Tabs>;
}
