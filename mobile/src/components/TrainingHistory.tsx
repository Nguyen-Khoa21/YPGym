import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Ellipse, Path, Rect } from 'react-native-svg';

import { Action, Busy, Card, Message, textStyles } from '@/components/ui';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { colors } from '@/lib/theme';
import { muscleLabels, type Muscle, type WorkoutDayDetail, type WorkoutHistoryDay, type WorkoutHistoryPage, type WorkoutWeekSummary } from '@/lib/training';

const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const intensityColors = [colors.surface, '#FEE2E2', '#FCA5A5', '#F87171', '#B91C1C'];
const intensityNames = ['No workout', 'Light', 'Moderate', 'High', 'Highest'];

export function TrainingHistory() {
  const { request, user } = useAuth();
  const [month, setMonth] = useState(() => monthKey(new Date()));
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const monthInfo = useMemo(() => getMonth(month), [month]);
  const history = useQuery({ queryKey: ['training', 'history', user?.id, month], queryFn: ({ signal }) => request<WorkoutHistoryPage>(`/training/workouts/history?date_from=${monthInfo.first}&date_to=${monthInfo.last}&page_size=100`, { signal }) });
  const week = useQuery({ queryKey: ['training', 'muscle-map', user?.id, 'current'], queryFn: ({ signal }) => request<WorkoutWeekSummary>('/training/workouts/muscle-map', { signal }) });
  const detail = useQuery({ queryKey: ['training', 'workout', user?.id, selectedDate], queryFn: ({ signal }) => request<WorkoutDayDetail>(`/training/workouts/${selectedDate}`, { signal }), enabled: !!selectedDate });
  const activity = new Map(history.data?.items.map((item) => [item.workout_date, item]));

  const moveMonth = (offset: number) => {
    const [year, value] = month.split('-').map(Number);
    setMonth(monthKey(new Date(year, value - 1 + offset, 1)));
    setSelectedDate(null);
  };

  return <>
    <Card><Text style={textStyles.accent}>ATTENDANCE AND WORKOUTS</Text><Text style={textStyles.subheading}>Workout calendar</Text><Text style={textStyles.muted}>Outlined dates are attended days. Red shades show relative weighted set exposure for logged workouts in this month.</Text>
      <View style={styles.monthControls}><View style={styles.monthAction}><Action label="Previous month" outline onPress={() => moveMonth(-1)} /></View><Text style={styles.monthLabel}>{monthInfo.label}</Text><View style={styles.monthAction}><Action label="Next month" outline onPress={() => moveMonth(1)} /></View></View>
      {history.isLoading ? <Busy label="Loading workout history" /> : null}
      {history.isError ? <Message title="History unavailable" detail={errorMessage(history.error)} action="Retry" onAction={() => void history.refetch()} tone="error" /> : null}
      {history.data ? <><View accessibilityRole="summary" style={styles.calendar}>{dayNames.map((name) => <Text key={name} style={styles.dayName}>{name}</Text>)}{Array.from({ length: monthInfo.offset }, (_, index) => <View key={`blank-${index}`} style={styles.dayCell} />)}{Array.from({ length: monthInfo.days }, (_, index) => { const day = index + 1; const iso = `${month}-${String(day).padStart(2, '0')}`; const item = activity.get(iso); return <CalendarDay key={iso} day={day} item={item} selected={selectedDate === iso} onPress={() => setSelectedDate(iso)} />; })}</View><View style={styles.legend}>{intensityNames.map((name, level) => <View key={name} style={styles.legendItem}><View style={[styles.legendSwatch, { backgroundColor: intensityColors[level] }]} /><Text style={styles.legendText}>{name}</Text></View>)}<View style={styles.legendItem}><View style={[styles.legendSwatch, { borderColor: colors.primary, borderWidth: 2 }]} /><Text style={styles.legendText}>Attended</Text></View></View>{history.data.items.length === 0 ? <Message title="No activity this month" detail="Scanner attendance and logged workouts will appear here." /> : null}</> : null}
      {selectedDate && detail.isLoading ? <Busy label="Loading selected day" /> : null}{selectedDate && detail.isError ? <Message title="Day unavailable" detail={errorMessage(detail.error)} action="Retry" onAction={() => void detail.refetch()} tone="error" /> : null}{detail.data ? <DayDetail value={detail.data} /> : null}
    </Card>
    <Card><Text style={textStyles.accent}>CURRENT MONDAY–SUNDAY WEEK</Text><Text style={textStyles.subheading}>Weekly muscle map</Text>{week.isLoading ? <Busy label="Calculating weekly exposure" /> : null}{week.isError ? <Message title="Muscle map unavailable" detail={errorMessage(week.error)} action="Retry" onAction={() => void week.refetch()} tone="error" /> : null}{week.data ? <MuscleMap value={week.data} /> : null}</Card>
  </>;
}

function CalendarDay({ day, item, selected, onPress }: { day: number; item?: WorkoutHistoryDay; selected: boolean; onPress: () => void }) {
  const label = item ? `${item.workout_date}: ${item.attended ? 'attended' : 'not attended'}; ${item.has_workout ? `${item.set_count} sets, ${item.exposure_score} weighted set exposure, ${intensityNames[item.intensity_level]} intensity` : 'no workout logged'}` : `${day}: no activity`;
  return <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{ disabled: !item, selected }} disabled={!item} onPress={onPress} style={({ pressed }) => [styles.dayCell, { backgroundColor: item?.has_workout ? intensityColors[item.intensity_level] : colors.white, borderColor: item?.attended ? colors.primary : colors.border, borderWidth: item?.attended ? 2 : 1 }, selected && styles.selected, pressed && styles.pressed]}><Text style={[styles.dayNumber, item?.intensity_level && item.intensity_level >= 3 ? styles.dayNumberLight : null]}>{day}</Text>{item?.has_workout ? <Text style={[styles.setCount, item.intensity_level >= 3 ? styles.dayNumberLight : null]}>{item.set_count} sets</Text> : null}</Pressable>;
}

function DayDetail({ value }: { value: WorkoutDayDetail }) {
  return <View style={styles.detail}><View style={styles.detailHeader}><Text style={textStyles.subheading}>{formatIsoDate(value.workout_date)}</Text><Text style={styles.attendance}>{value.attended ? 'ATTENDED' : 'WORKOUT ONLY'}</Text></View><Text style={textStyles.muted}>{value.exposure_score} weighted set exposure</Text>{value.session ? value.session.exercises.map((exercise) => <View key={exercise.id} style={styles.exercise}><Text style={textStyles.body}>{exercise.name}</Text><Text style={textStyles.muted}>{exercise.sets.map((set) => `${set.set_order}: ${set.reps} reps × ${set.weight} ${set.unit}`).join(' · ')}</Text></View>) : <Text style={textStyles.body}>You attended the gym but did not log a workout.</Text>}</View>;
}

function MuscleMap({ value }: { value: WorkoutWeekSummary }) {
  const levels = Object.fromEntries(value.muscles.map((item) => [item.muscle, item.intensity_level])) as Record<Muscle, 0 | 1 | 2 | 3 | 4>;
  return <View style={styles.map}><Text style={textStyles.muted}>{formatIsoDate(value.week_start)}–{formatIsoDate(value.week_end)} · {value.total_exposure_score} total exposure</Text><Text style={textStyles.body}>{value.metric.description} {value.metric.bodyweight_handling}</Text><View style={styles.figures}><BodyFigure side="Front" levels={levels} /><BodyFigure side="Back" levels={levels} /></View><Text style={textStyles.subheading}>Muscle-by-muscle exposure</Text>{value.muscles.map((item) => <View key={item.muscle} style={styles.muscleRow}><Text style={styles.muscleName}>{muscleLabels[item.muscle]}</Text><Text style={styles.muscleValue}>{item.exposure_score} · {intensityNames[item.intensity_level]}</Text></View>)}<Text style={textStyles.muted}>This diagram summarizes logged set exposure. It does not measure anatomical activation or provide a training prescription.</Text></View>;
}

function BodyFigure({ side, levels }: { side: 'Front' | 'Back'; levels: Record<Muscle, 0 | 1 | 2 | 3 | 4> }) {
  const fill = (muscle: Muscle) => intensityColors[levels[muscle] ?? 0];
  return <View style={styles.figure} accessibilityLabel={`${side} muscle exposure diagram`}><Svg width="130" height="260" viewBox="0 0 140 300"><Circle cx="70" cy="24" r="18" fill="#D1D5DB" /><Rect x="50" y="44" width="40" height="94" rx="18" fill="#E5E7EB" /><Rect x="34" y="52" width="16" height="105" rx="8" fill="#E5E7EB" /><Rect x="90" y="52" width="16" height="105" rx="8" fill="#E5E7EB" /><Rect x="51" y="135" width="18" height="140" rx="9" fill="#E5E7EB" /><Rect x="71" y="135" width="18" height="140" rx="9" fill="#E5E7EB" />{side === 'Front' ? <><Circle cx="49" cy="58" r="10" fill={fill('shoulders')} /><Circle cx="91" cy="58" r="10" fill={fill('shoulders')} /><Rect x="54" y="57" width="32" height="26" rx="8" fill={fill('chest')} /><Rect x="36" y="68" width="12" height="34" rx="6" fill={fill('biceps')} /><Rect x="92" y="68" width="12" height="34" rx="6" fill={fill('biceps')} /><Rect x="35" y="105" width="11" height="43" rx="5" fill={fill('forearms')} /><Rect x="94" y="105" width="11" height="43" rx="5" fill={fill('forearms')} /><Rect x="58" y="86" width="24" height="43" rx="7" fill={fill('core')} /><Rect x="53" y="143" width="15" height="64" rx="7" fill={fill('quadriceps')} /><Rect x="72" y="143" width="15" height="64" rx="7" fill={fill('quadriceps')} /><Rect x="54" y="215" width="13" height="50" rx="6" fill={fill('calves')} /><Rect x="73" y="215" width="13" height="50" rx="6" fill={fill('calves')} /></> : <><Circle cx="49" cy="58" r="10" fill={fill('shoulders')} /><Circle cx="91" cy="58" r="10" fill={fill('shoulders')} /><Path d="M54 61 Q70 50 86 61 L82 112 Q70 128 58 112 Z" fill={fill('back')} /><Rect x="36" y="70" width="12" height="34" rx="6" fill={fill('triceps')} /><Rect x="92" y="70" width="12" height="34" rx="6" fill={fill('triceps')} /><Rect x="35" y="107" width="11" height="41" rx="5" fill={fill('forearms')} /><Rect x="94" y="107" width="11" height="41" rx="5" fill={fill('forearms')} /><Ellipse cx="61" cy="145" rx="10" ry="13" fill={fill('glutes')} /><Ellipse cx="79" cy="145" rx="10" ry="13" fill={fill('glutes')} /><Rect x="53" y="158" width="15" height="51" rx="7" fill={fill('hamstrings')} /><Rect x="72" y="158" width="15" height="51" rx="7" fill={fill('hamstrings')} /><Rect x="54" y="215" width="13" height="50" rx="6" fill={fill('calves')} /><Rect x="73" y="215" width="13" height="50" rx="6" fill={fill('calves')} /></>}</Svg><Text style={styles.figureLabel}>{side}</Text></View>;
}

function monthKey(value: Date) { return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`; }
function getMonth(value: string) { const [year, month] = value.split('-').map(Number); const days = new Date(year, month, 0).getDate(); return { first: `${value}-01`, last: `${value}-${String(days).padStart(2, '0')}`, days, offset: (new Date(year, month - 1, 1).getDay() + 6) % 7, label: new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }).format(new Date(year, month - 1, 1)) }; }
function formatIsoDate(value: string) { return new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`)); }

const styles = StyleSheet.create({
  monthControls: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8 }, monthAction: { flex: 1 }, monthLabel: { color: colors.text, fontWeight: '900', textAlign: 'center', flex: 1 },
  calendar: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', marginTop: 10 }, dayName: { width: '13%', textAlign: 'center', color: colors.muted, fontSize: 10, fontWeight: '800', marginBottom: 4 }, dayCell: { width: '13%', aspectRatio: 1, minHeight: 40, borderRadius: 10, alignItems: 'center', justifyContent: 'center', marginBottom: 5 }, dayNumber: { color: colors.text, fontWeight: '900' }, dayNumberLight: { color: colors.white }, setCount: { fontSize: 8, color: colors.text, fontWeight: '800' }, selected: { borderColor: colors.positive, borderWidth: 3 }, pressed: { opacity: 0.78 },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 10 }, legendItem: { flexDirection: 'row', alignItems: 'center', gap: 5 }, legendSwatch: { width: 15, height: 15, borderRadius: 4 }, legendText: { color: colors.muted, fontSize: 11 },
  detail: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: 16, padding: 15, gap: 6, marginTop: 8 }, detailHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 }, attendance: { color: colors.primary, fontSize: 10, fontWeight: '900' }, exercise: { borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 10, marginTop: 5 },
  map: { gap: 10 }, figures: { flexDirection: 'row', justifyContent: 'space-around', backgroundColor: colors.surface, borderRadius: 16, paddingVertical: 10 }, figure: { alignItems: 'center', flex: 1 }, figureLabel: { color: colors.text, fontWeight: '900' }, muscleRow: { minHeight: 42, borderWidth: 1, borderColor: colors.border, borderRadius: 12, paddingHorizontal: 12, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 }, muscleName: { color: colors.text, textTransform: 'capitalize' }, muscleValue: { color: colors.text, fontWeight: '800', textAlign: 'right' },
});
