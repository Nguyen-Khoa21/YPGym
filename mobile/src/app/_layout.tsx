import { QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { AuthProvider } from '@/lib/auth';
import { queryClient } from '@/lib/query';
import { colors } from '@/lib/theme';

export default function RootLayout() {
  return <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <StatusBar style="light" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }} />
    </AuthProvider>
  </QueryClientProvider>;
}
