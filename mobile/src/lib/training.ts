export const muscles = ['chest', 'back', 'shoulders', 'biceps', 'triceps', 'forearms', 'core', 'quadriceps', 'hamstrings', 'glutes', 'calves'] as const;
export type Muscle = typeof muscles[number];
export type Exercise = { id: string; name: string; description: string; region: 'upper' | 'lower'; usage_steps: string; safety_note: string; primary_muscles: Muscle[]; secondary_muscles: Muscle[]; is_illustrative: boolean; is_active: boolean; has_image: boolean; created_at: string; updated_at: string };
export type ExercisePage = { items: Exercise[]; page: { page: number; page_size: number; total: number; pages: number } };
export function exerciseImage(item: Exercise) { return `/training/exercises/${item.id}/image?v=${encodeURIComponent(item.updated_at)}`; }
