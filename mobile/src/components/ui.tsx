import type { PropsWithChildren, ReactNode } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View, type TextInputProps } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { colors } from '@/lib/theme';

export function Screen({ children, onRefresh, refreshing = false }: PropsWithChildren<{ onRefresh?: () => void; refreshing?: boolean }>) {
  return <SafeAreaView style={styles.screen}>
    <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.screenContent} refreshControl={onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.lime} /> : undefined}>
      <View style={styles.column}>{children}</View>
    </ScrollView>
  </SafeAreaView>;
}

export function Brand({ right }: { right?: ReactNode }) {
  return <View style={styles.brand}><Text style={styles.brandMark}>✕</Text><Text style={styles.brandName}>YPGym</Text><View style={styles.brandRight}>{right}</View></View>;
}

export function Heading({ eyebrow, title, detail }: { eyebrow?: string; title: string; detail?: string }) {
  return <View style={{ gap: 5, marginBottom: 20 }}>
    {eyebrow ? <Text style={styles.eyebrow}>{eyebrow}</Text> : null}
    <Text style={styles.heading}>{title}</Text>
    {detail ? <Text style={styles.muted}>{detail}</Text> : null}
  </View>;
}

export function PageTop({ title, onBack }: { title: string; onBack: () => void }) {
  return <View style={styles.pageTop}><Pressable accessibilityRole="button" accessibilityLabel="Go back" onPress={onBack} style={styles.back}><Ionicons name="arrow-back" size={25} color={colors.text} /></Pressable><Text style={styles.pageTopTitle}>{title}</Text></View>;
}

export function Card({ children, accent = false }: PropsWithChildren<{ accent?: boolean }>) {
  return <View style={[styles.card, accent && styles.accentCard]}>{children}</View>;
}

export function Action({ label, onPress, outline = false, danger = false, disabled = false }: { label: string; onPress: () => void; outline?: boolean; danger?: boolean; disabled?: boolean }) {
  return <Pressable accessibilityRole="button" accessibilityState={{ disabled }} disabled={disabled} onPress={onPress} style={({ pressed }) => [styles.action, outline && styles.outline, danger && styles.danger, (pressed || disabled) && { opacity: 0.65 }]}>
    <Text style={[styles.actionText, (outline || danger) && { color: danger ? colors.coral : colors.text }]}>{label}</Text>
  </Pressable>;
}

export function Field({ label, value, onChangeText, ...props }: TextInputProps & { label: string; value: string; onChangeText: (value: string) => void }) {
  return <View style={{ gap: 8 }}><Text style={styles.fieldLabel}>{label}</Text><TextInput accessibilityLabel={label} placeholderTextColor={colors.dim} selectionColor={colors.lime} style={styles.input} value={value} onChangeText={onChangeText} {...props} /></View>;
}

export function Busy({ label }: { label: string }) { return <View style={styles.message}><ActivityIndicator color={colors.lime} size="large" /><Text style={styles.muted}>{label}</Text></View>; }
export function Message({ title, detail, action, onAction }: { title: string; detail: string; action?: string; onAction?: () => void }) {
  return <View style={styles.message}><Text style={styles.subheading}>{title}</Text><Text style={[styles.muted, { textAlign: 'center' }]}>{detail}</Text>{action && onAction ? <Action label={action} onPress={onAction} outline /> : null}</View>;
}
export function Pill({ label, tone = 'lime', centered = false }: { label: string; tone?: 'lime' | 'amber' | 'coral'; centered?: boolean }) {
  const foreground = colors[tone];
  return <View style={[styles.pill, { borderColor: foreground }, centered && { alignSelf: 'center' }]}><Text style={[styles.pillText, { color: foreground }]}>{label.toUpperCase()}</Text></View>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  screenContent: { flexGrow: 1, paddingHorizontal: 20, paddingBottom: 38, alignItems: 'center' },
  column: { width: '100%', maxWidth: 600 },
  brand: { minHeight: 66, borderBottomWidth: 1, borderBottomColor: colors.border, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 23 },
  brandMark: { color: colors.lime, fontSize: 27, fontWeight: '900', width: 45 },
  brandName: { color: colors.lime, fontSize: 27, fontWeight: '900', letterSpacing: -1 },
  brandRight: { width: 45, alignItems: 'flex-end' },
  pageTop: { minHeight: 63, flexDirection: 'row', alignItems: 'center', borderBottomColor: colors.border, borderBottomWidth: 1, marginBottom: 23 },
  back: { paddingRight: 16, paddingVertical: 10 },
  pageTopTitle: { color: colors.lime, fontSize: 24, fontWeight: '800', flexShrink: 1 },
  heading: { color: colors.text, fontSize: 28, fontWeight: '800', lineHeight: 34 },
  subheading: { color: colors.text, fontSize: 22, fontWeight: '800' },
  body: { color: colors.text, fontSize: 16, lineHeight: 23 },
  muted: { color: colors.muted, fontSize: 14, lineHeight: 21 },
  lime: { color: colors.lime, fontWeight: '800' },
  eyebrow: { color: colors.lime, fontSize: 11, fontWeight: '800', letterSpacing: 1.8, textTransform: 'uppercase' },
  card: { backgroundColor: colors.card, borderColor: colors.border, borderWidth: 1, borderRadius: 13, padding: 20, gap: 11, marginBottom: 12 },
  accentCard: { borderLeftColor: colors.lime, borderLeftWidth: 2 },
  action: { minHeight: 51, paddingHorizontal: 18, borderRadius: 6, backgroundColor: colors.lime, alignItems: 'center', justifyContent: 'center' },
  outline: { backgroundColor: 'transparent', borderColor: colors.border, borderWidth: 1 },
  danger: { backgroundColor: 'transparent', borderColor: colors.coral, borderWidth: 1 },
  actionText: { color: colors.black, fontSize: 16, fontWeight: '800' },
  fieldLabel: { color: colors.text, fontSize: 13, fontWeight: '700' },
  input: { minHeight: 49, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border, borderRadius: 7, paddingHorizontal: 14, color: colors.text, fontSize: 16 },
  message: { backgroundColor: colors.cardAlt, borderColor: colors.border, borderWidth: 1, borderRadius: 14, padding: 25, alignItems: 'center', gap: 12, marginVertical: 15 },
  pill: { alignSelf: 'flex-start', borderWidth: 1, borderRadius: 15, paddingHorizontal: 10, paddingVertical: 4 },
  pillText: { fontSize: 10, fontWeight: '800', letterSpacing: 1 },
});

export const textStyles = StyleSheet.create({ heading: styles.heading, subheading: styles.subheading, body: styles.body, muted: styles.muted, lime: styles.lime, eyebrow: styles.eyebrow });
