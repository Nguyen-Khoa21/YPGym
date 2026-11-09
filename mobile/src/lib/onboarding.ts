export type OnboardingStatus = 'not_started' | 'skipped' | 'partial' | 'complete';

export type OnboardingState = {
  status: OnboardingStatus;
  is_new_to_gym?: boolean | null;
  prefers_uncrowded_hours?: boolean | null;
  closer_gym_id?: string | null;
  main_goal?: string | null;
  training_window?: string | null;
  days_per_week?: string | null;
  interested_in_classes?: boolean | null;
  interested_in_personal_trainer?: boolean | null;
};

export type Recommendations = {
  recommended_gym?: { id: string; name: string; slug: string; district: string };
  quiet_hours?: { gym_id: string; gym_name: string; label: string; start_hour: number; end_hour: number; average_capacity_percentage: number };
  quiet_hours_reason?: 'not_enough_data';
};

export type Option = { value: string; label: string };

export const yesNoOptions: Option[] = [{ value: 'yes', label: 'Yes' }, { value: 'no', label: 'No' }];
export const goalOptions: Option[] = [
  { value: 'lose_weight', label: 'Lose weight' },
  { value: 'build_muscle', label: 'Build muscle' },
  { value: 'stay_fit', label: 'Stay fit and healthy' },
  { value: 'stamina', label: 'Improve stamina' },
  { value: 'not_sure', label: 'Not sure yet' },
];
export const windowOptions: Option[] = [
  { value: 'early_morning', label: 'Early morning (05:00 to 08:00)' },
  { value: 'daytime', label: 'Daytime (08:00 to 16:00)' },
  { value: 'evening', label: 'Evening (16:00 to 20:00)' },
  { value: 'night', label: 'Night (20:00 to 24:00)' },
];
export const daysOptions: Option[] = [
  { value: '1_2', label: '1 to 2 days' },
  { value: '3_4', label: '3 to 4 days' },
  { value: '5_plus', label: '5 or more days' },
];

export const fromBoolean = (value: boolean | null | undefined) => (value === true ? 'yes' : value === false ? 'no' : '');
export const toBoolean = (value: string) => (value === 'yes' ? true : value === 'no' ? false : null);

// Asked once per app session when the member has not answered or skipped yet.
export function shouldPromptOnboarding(status: OnboardingStatus | undefined, alreadyPrompted: boolean) {
  return status === 'not_started' && !alreadyPrompted;
}
