export const MUSCLES = ["chest", "back", "shoulders", "biceps", "triceps", "forearms", "core", "quadriceps", "hamstrings", "glutes", "calves"] as const;
export type Muscle = typeof MUSCLES[number];
export type Exercise = {
  id: string;
  name: string;
  description: string;
  region: "upper" | "lower";
  usage_steps: string;
  safety_note: string;
  primary_muscles: Muscle[];
  secondary_muscles: Muscle[];
  is_illustrative: boolean;
  is_active: boolean;
  has_image: boolean;
  created_at: string;
  updated_at: string;
};
export type ExercisePage = { items: Exercise[]; page: { page: number; page_size: number; total: number; pages: number } };
export function exerciseImage(item: Exercise) { return `/training/exercises/${item.id}/image?v=${encodeURIComponent(item.updated_at)}`; }
export type WorkoutSet = { id: string; set_order: number; reps: number; weight: string; unit: "kg" | "lb" };
export type WorkoutSession = {
  id: string;
  workout_date: string;
  attendance_session_id: string;
  exercises: { id: string; exercise_id: string; name: string; primary_muscles: Muscle[]; secondary_muscles: Muscle[]; created_at: string; sets: WorkoutSet[] }[];
};
export type WorkoutToday = {
  gym_date: string;
  gym_timezone: string;
  eligible: boolean;
  reason: string | null;
  session: WorkoutSession | null;
};
export type ExposureMetric = { key: "weighted_set_exposure"; label: string; description: string; bodyweight_handling: string; primary_weight: string; secondary_weight: string };
export type WorkoutHistoryDay = { workout_date: string; attended: boolean; has_workout: boolean; exercise_count: number; set_count: number; exposure_score: string; intensity_level: 0 | 1 | 2 | 3 | 4 };
export type WorkoutHistoryPage = { gym_timezone: string; date_from: string; date_to: string; metric: ExposureMetric; max_exposure_score: string; items: WorkoutHistoryDay[]; page: { page: number; page_size: number; total: number; pages: number } };
export type WorkoutDayDetail = { gym_timezone: string; workout_date: string; attended: boolean; exposure_score: string; metric: ExposureMetric; session: WorkoutSession | null };
export type ExerciseHistoryPage = {
  gym_timezone: string;
  items: { workout_date: string; workout_exercise_id: string; name: string; sets: WorkoutSet[]; set_count: number; total_reps: number; max_external_load_kg: string; comparison_to_previous: null | { sets: "more" | "same" | "less"; reps: "more" | "same" | "less"; external_load: "more" | "same" | "less" } }[];
  page: { page: number; page_size: number; total: number; pages: number };
};
export type WorkoutWeekSummary = { gym_timezone: string; week_start: string; week_end: string; metric: ExposureMetric; total_exposure_score: string; max_muscle_exposure_score: string; days: WorkoutHistoryDay[]; muscles: { muscle: Muscle; exposure_score: string; intensity_level: 0 | 1 | 2 | 3 | 4 }[] };
