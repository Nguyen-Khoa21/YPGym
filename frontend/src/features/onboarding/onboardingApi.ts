import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";

export type OnboardingStatus = "not_started" | "skipped" | "partial" | "complete";

export type OnboardingAnswers = {
  is_new_to_gym: boolean | null;
  prefers_uncrowded_hours: boolean | null;
  closer_gym_id: string | null;
  main_goal: string | null;
  training_window: string | null;
  days_per_week: string | null;
  interested_in_classes: boolean | null;
  interested_in_personal_trainer: boolean | null;
};

export type OnboardingState = Partial<OnboardingAnswers> & { status: OnboardingStatus };

export type Recommendations = {
  recommended_gym?: { id: string; name: string; slug: string; district: string };
  quiet_hours?: {
    gym_id: string;
    gym_name: string;
    label: string;
    start_hour: number;
    end_hour: number;
    average_capacity_percentage: number;
  };
  quiet_hours_reason?: "not_enough_data";
};

export const goalOptions = [
  { value: "lose_weight", label: "Lose weight" },
  { value: "build_muscle", label: "Build muscle" },
  { value: "stay_fit", label: "Stay fit and healthy" },
  { value: "stamina", label: "Improve stamina" },
  { value: "not_sure", label: "Not sure yet" },
] as const;

export const windowOptions = [
  { value: "early_morning", label: "Early morning (05:00 to 08:00)" },
  { value: "daytime", label: "Daytime (08:00 to 16:00)" },
  { value: "evening", label: "Evening (16:00 to 20:00)" },
  { value: "night", label: "Night (20:00 to 24:00)" },
] as const;

export const daysOptions = [
  { value: "1_2", label: "1 to 2 days" },
  { value: "3_4", label: "3 to 4 days" },
  { value: "5_plus", label: "5 or more days" },
] as const;

export function useOnboarding(enabled = true) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["onboarding", "me"],
    enabled: enabled && Boolean(token),
    queryFn: ({ signal }) => apiRequest<OnboardingState>("/users/me/onboarding", { token, signal }),
  });
}

/** Recommendations are computed on the server from the member's own answers; no answer means no recommendation. */
export function useRecommendations(enabled = true) {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["recommendations", "me"],
    enabled: enabled && Boolean(token),
    staleTime: 300_000,
    queryFn: ({ signal }) =>
      apiRequest<Recommendations>("/users/me/recommendations", { token, signal }),
  });
}
