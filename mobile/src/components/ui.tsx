import type { PropsWithChildren, ReactNode } from 'react';
import { router, type Href } from 'expo-router';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  useWindowDimensions,
  type StyleProp,
  type TextInputProps,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { colors, radii, shadows, spacing } from '@/lib/theme';
import { goBackOrReplace } from '@/lib/navigation';

export function Screen({ children, onRefresh, refreshing = false }: PropsWithChildren<{ onRefresh?: () => void; refreshing?: boolean }>) {
  const { width } = useWindowDimensions();
  const horizontalPadding = width >= 900 ? 32 : width >= 600 ? 26 : 18;
  return <SafeAreaView style={styles.screen}>
    <ScrollView
      automaticallyAdjustKeyboardInsets
      contentInsetAdjustmentBehavior="automatic"
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
      contentContainerStyle={[styles.screenContent, { paddingHorizontal: horizontalPadding }]}
      refreshControl={onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} colors={[colors.primary]} /> : undefined}
    >
      <View style={styles.column}>{children}</View>
    </ScrollView>
  </SafeAreaView>;
}

export function Brand({ right }: { right?: ReactNode }) {
  return <View style={styles.brand}>
    <View style={styles.brandLockup}><View style={styles.brandMark}><Ionicons name="barbell" size={20} color={colors.white} /></View><Text style={styles.brandName}>YPGYM</Text></View>
    <View style={styles.brandRight}>{right}</View>
  </View>;
}

export function IconButton({ icon, label, onPress }: { icon: keyof typeof Ionicons.glyphMap; label: string; onPress: () => void }) {
  return <Pressable accessibilityRole="button" accessibilityLabel={label} hitSlop={6} onPress={onPress} style={({ pressed }) => [styles.iconButton, pressed && styles.pressed]}>
    <Ionicons name={icon} size={23} color={colors.primary} />
  </Pressable>;
}

export function Heading({ eyebrow, title, detail }: { eyebrow?: string; title: string; detail?: string }) {
  return <View style={styles.headingBlock}>
    {eyebrow ? <Text style={styles.eyebrow}>{eyebrow}</Text> : null}
    <Text style={styles.heading}>{title}</Text>
    {detail ? <Text style={styles.muted}>{detail}</Text> : null}
  </View>;
}

export function PageTop({ title, fallback }: { title: string; fallback: Href }) {
  return <View style={styles.pageTop}><Pressable accessibilityRole="button" accessibilityLabel="Go back" hitSlop={6} onPress={() => goBackOrReplace(router, fallback)} style={({ pressed }) => [styles.back, pressed && styles.pressed]}><Ionicons name="arrow-back" size={24} color={colors.primary} /></Pressable><Text style={styles.pageTopTitle}>{title}</Text></View>;
}

export function Card({ children, accent = false, style }: PropsWithChildren<{ accent?: boolean; style?: StyleProp<ViewStyle> }>) {
  return <View style={[styles.card, accent && styles.accentCard, style]}>
    {accent ? <Ionicons pointerEvents="none" name="barbell-outline" size={76} color={colors.positive} style={styles.cardMotif} /> : null}
    <View style={styles.cardContent}>{children}</View>
  </View>;
}

export function Action({ label, onPress, outline = false, danger = false, disabled = false }: { label: string; onPress: () => void; outline?: boolean; danger?: boolean; disabled?: boolean }) {
  return <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{ disabled }} disabled={disabled} onPress={onPress} style={({ pressed }) => [styles.action, outline && styles.outline, danger && styles.danger, pressed && !disabled && styles.pressed, disabled && styles.disabled]}>
    <Text style={[styles.actionText, outline && styles.outlineText, danger && styles.dangerText]}>{label}</Text>
  </Pressable>;
}

export function Field({ label, value, onChangeText, error, ...props }: TextInputProps & { label: string; value: string; onChangeText: (value: string) => void; error?: string }) {
  return <View style={styles.field}><Text style={styles.fieldLabel}>{label}</Text><TextInput accessibilityLabel={label} accessibilityHint={error} placeholderTextColor={colors.dim} selectionColor={colors.primary} style={[styles.input, error && styles.inputError]} value={value} onChangeText={onChangeText} {...props} />{error ? <View style={styles.fieldError}><Ionicons name="alert-circle-outline" size={16} color={colors.danger} /><Text style={styles.fieldErrorText}>{error}</Text></View> : null}</View>;
}

export function Busy({ label }: { label: string }) {
  return <View style={styles.loadingCard} accessibilityRole="progressbar" accessibilityLabel={label}>
    <View style={styles.loadingTitle}><ActivityIndicator color={colors.primary} /><Text style={styles.muted}>{label}</Text></View>
    <View style={styles.skeletonWide} /><View style={styles.skeletonMedium} /><View style={styles.skeletonShort} />
  </View>;
}

type MessageTone = 'neutral' | 'error' | 'success';
export function Message({ title, detail, action, onAction, tone = 'neutral' }: { title: string; detail: string; action?: string; onAction?: () => void; tone?: MessageTone }) {
  const icon = tone === 'error' ? 'alert-circle-outline' : tone === 'success' ? 'checkmark-circle-outline' : 'information-circle-outline';
  const iconColor = tone === 'error' ? colors.danger : tone === 'success' ? colors.positive : colors.primary;
  return <View accessibilityRole={tone === 'error' ? 'alert' : undefined} style={[styles.message, tone === 'error' && styles.messageError, tone === 'success' && styles.messageSuccess]}>
    <View style={[styles.messageIcon, tone === 'error' && styles.messageIconError, tone === 'success' && styles.messageIconSuccess]}><Ionicons name={icon} size={22} color={iconColor} /></View>
    <View style={styles.messageCopy}><Text style={styles.messageTitle}>{title}</Text><Text style={styles.muted}>{detail}</Text>{action && onAction ? <Action label={action} onPress={onAction} outline /> : null}</View>
  </View>;
}

type PillTone = 'positive' | 'warning' | 'danger' | 'neutral';
export function Pill({ label, tone = 'positive', centered = false }: { label: string; tone?: PillTone; centered?: boolean }) {
  const palette = {
    positive: { foreground: colors.primary, background: colors.positiveSurface, icon: 'checkmark-circle' as const },
    warning: { foreground: colors.warning, background: colors.warningSurface, icon: 'alert-circle' as const },
    danger: { foreground: colors.danger, background: colors.dangerSurface, icon: 'close-circle' as const },
    neutral: { foreground: colors.muted, background: colors.surface, icon: 'ellipse' as const },
  }[tone];
  return <View style={[styles.pill, { backgroundColor: palette.background }, centered && styles.centered]}><Ionicons name={palette.icon} size={13} color={palette.foreground} /><Text style={[styles.pillText, { color: palette.foreground }]}>{label.toUpperCase()}</Text></View>;
}

export function SectionTitle({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) {
  return <View style={styles.sectionTitle}><Text style={styles.subheading}>{title}</Text>{action && onAction ? <Pressable accessibilityRole="button" hitSlop={8} onPress={onAction} style={({ pressed }) => [styles.sectionAction, pressed && styles.pressed]}><Text style={styles.accentText}>{action}</Text></Pressable> : null}</View>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  screenContent: { flexGrow: 1, paddingBottom: 44, alignItems: 'center' },
  column: { width: '100%', maxWidth: 760 },
  brand: { minHeight: 72, borderBottomWidth: 1, borderBottomColor: colors.border, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: spacing.lg },
  brandLockup: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  brandMark: { width: 40, height: 40, borderRadius: 13, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.primary },
  brandName: { color: colors.primary, fontSize: 23, fontWeight: '900', letterSpacing: 1.2 },
  brandRight: { minWidth: 48, alignItems: 'flex-end' },
  iconButton: { width: 48, height: 48, borderRadius: 16, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.primarySurface },
  headingBlock: { gap: 6, marginBottom: spacing.lg },
  pageTop: { minHeight: 68, flexDirection: 'row', alignItems: 'center', borderBottomColor: colors.border, borderBottomWidth: 1, marginBottom: spacing.lg },
  back: { width: 48, height: 48, marginLeft: -8, marginRight: 4, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  pageTopTitle: { color: colors.text, fontSize: 23, fontWeight: '900', letterSpacing: -0.45, flexShrink: 1 },
  heading: { color: colors.text, fontSize: 32, fontWeight: '900', lineHeight: 37, letterSpacing: -0.9 },
  subheading: { color: colors.text, fontSize: 21, fontWeight: '900', lineHeight: 26, letterSpacing: -0.35 },
  body: { color: colors.text, fontSize: 16, lineHeight: 24 },
  muted: { color: colors.muted, fontSize: 14, lineHeight: 21 },
  accentText: { color: colors.primary, fontWeight: '800' },
  eyebrow: { color: colors.primary, fontSize: 11, fontWeight: '900', letterSpacing: 1.7, textTransform: 'uppercase' },
  card: { position: 'relative', overflow: 'hidden', backgroundColor: colors.card, borderColor: colors.border, borderWidth: 1, borderRadius: radii.lg, marginBottom: 14, ...shadows.card },
  cardContent: { padding: 20, gap: 11, zIndex: 1 },
  accentCard: { backgroundColor: colors.primarySurface, borderColor: colors.positiveBorder },
  cardMotif: { position: 'absolute', right: -13, top: -13, opacity: 0.12, transform: [{ rotate: '-18deg' }] },
  action: { minHeight: 52, paddingHorizontal: 18, borderRadius: radii.md, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  outline: { backgroundColor: colors.white, borderColor: colors.primary, borderWidth: 1 },
  danger: { backgroundColor: colors.dangerSurface, borderColor: colors.dangerBorder, borderWidth: 1 },
  actionText: { color: colors.white, fontSize: 16, fontWeight: '800' },
  outlineText: { color: colors.primary },
  dangerText: { color: colors.danger },
  pressed: { transform: [{ scale: 0.97 }], opacity: 0.9 },
  disabled: { opacity: 0.48 },
  field: { gap: 8 },
  fieldLabel: { color: colors.text, fontSize: 13, fontWeight: '800' },
  input: { minHeight: 52, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, paddingHorizontal: 15, color: colors.text, fontSize: 16 },
  inputError: { borderColor: colors.danger, backgroundColor: colors.dangerSurface },
  fieldError: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  fieldErrorText: { flex: 1, color: colors.danger, fontSize: 13, lineHeight: 18, fontWeight: '600' },
  loadingCard: { backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: radii.lg, padding: 20, gap: 11, marginVertical: 15 },
  loadingTitle: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 3 },
  skeletonWide: { height: 12, width: '100%', borderRadius: radii.pill, backgroundColor: colors.surfaceStrong },
  skeletonMedium: { height: 12, width: '72%', borderRadius: radii.pill, backgroundColor: colors.surfaceStrong },
  skeletonShort: { height: 12, width: '46%', borderRadius: radii.pill, backgroundColor: colors.surfaceStrong },
  message: { flexDirection: 'row', backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1, borderRadius: radii.lg, padding: 18, gap: 13, marginVertical: 15 },
  messageError: { backgroundColor: colors.dangerSurface, borderColor: colors.dangerBorder },
  messageSuccess: { backgroundColor: colors.positiveSurface, borderColor: colors.positiveBorder },
  messageIcon: { width: 38, height: 38, borderRadius: 13, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.primarySurface },
  messageIconError: { backgroundColor: colors.dangerSurfaceStrong },
  messageIconSuccess: { backgroundColor: colors.surfaceStrong },
  messageCopy: { flex: 1, gap: 7 },
  messageTitle: { color: colors.text, fontSize: 17, lineHeight: 22, fontWeight: '900' },
  pill: { alignSelf: 'flex-start', minHeight: 30, borderRadius: radii.pill, paddingHorizontal: 10, paddingVertical: 5, flexDirection: 'row', alignItems: 'center', gap: 5 },
  pillText: { fontSize: 10, fontWeight: '900', letterSpacing: 0.9 },
  centered: { alignSelf: 'center' },
  sectionTitle: { minHeight: 48, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginTop: 18, marginBottom: 9 },
  sectionAction: { minHeight: 44, minWidth: 44, alignItems: 'flex-end', justifyContent: 'center' },
});

export const textStyles = StyleSheet.create({ heading: styles.heading, subheading: styles.subheading, body: styles.body, muted: styles.muted, accent: styles.accentText, eyebrow: styles.eyebrow });
