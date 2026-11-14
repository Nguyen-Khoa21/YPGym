import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm, type UseFormRegister } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { Button } from "@/components/ui/Button";
import { FieldError } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { queryClient } from "@/lib/queryClient";
import type { GymLocation } from "@/types/operations";
import {
  daysOptions,
  goalOptions,
  useOnboarding,
  windowOptions,
  type OnboardingState,
} from "./onboardingApi";

const yesNo = z
  .string()
  .refine((value): boolean => ["yes", "no"].includes(value), "Choose Yes or No.");
const schema = z.object({
  is_new_to_gym: yesNo,
  prefers_uncrowded_hours: yesNo,
  closer_gym_id: z.string().min(1, "Choose the location closest to you."),
  main_goal: z.string(),
  training_window: z.string(),
  days_per_week: z.string(),
  interested_in_classes: z.string(),
  interested_in_personal_trainer: z.string(),
});
type FormValues = z.infer<typeof schema>;
type Option = { value: string; label: string };

const yesNoOptions: Option[] = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
];
const fromBoolean = (value: boolean | null | undefined) =>
  value === true ? "yes" : value === false ? "no" : "";
const toBoolean = (value: string) => (value === "yes" ? true : value === "no" ? false : null);
const toText = (value: string) => value || null;

function toFormValues(data?: OnboardingState): FormValues {
  return {
    is_new_to_gym: fromBoolean(data?.is_new_to_gym),
    prefers_uncrowded_hours: fromBoolean(data?.prefers_uncrowded_hours),
    closer_gym_id: data?.closer_gym_id ?? "",
    main_goal: data?.main_goal ?? "",
    training_window: data?.training_window ?? "",
    days_per_week: data?.days_per_week ?? "",
    interested_in_classes: fromBoolean(data?.interested_in_classes),
    interested_in_personal_trainer: fromBoolean(data?.interested_in_personal_trainer),
  };
}

function RadioGroup({
  legend,
  name,
  options,
  register,
  error,
  optional = false,
}: {
  legend: string;
  name: keyof FormValues;
  options: Option[];
  register: UseFormRegister<FormValues>;
  error?: string;
  optional?: boolean;
}) {
  return (
    <fieldset className="rounded-2xl border border-border bg-card p-4">
      <legend className="px-1 text-sm font-extrabold">
        {legend}
        {optional ? (
          <span className="ml-2 text-xs font-semibold text-muted-foreground">Optional</span>
        ) : null}
      </legend>
      <div className="mt-2 flex flex-wrap gap-2">
        {options.map((option) => (
          <label
            className="flex min-h-11 cursor-pointer items-center gap-2 rounded-full border border-input px-4 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary/10"
            key={option.value}
          >
            <input type="radio" value={option.value} {...register(name)} />
            {option.label}
          </label>
        ))}
      </div>
      <FieldError message={error} />
    </fieldset>
  );
}

export function OnboardingForm({
  showSkip = false,
  onDone,
}: {
  showSkip?: boolean;
  onDone?: () => void;
}) {
  const { token } = useAuth();
  const onboarding = useOnboarding();
  const gyms = useQuery({
    queryKey: ["gyms", "active"],
    queryFn: ({ signal }) => apiRequest<GymLocation[]>("/gyms", { signal }),
  });
  const [error, setError] = useState<ReturnType<typeof toUiError> | null>(null);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: toFormValues(),
  });

  useEffect(() => {
    if (onboarding.data) form.reset(toFormValues(onboarding.data));
  }, [form, onboarding.data]);

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ["onboarding"] });
    void queryClient.invalidateQueries({ queryKey: ["recommendations"] });
  }
  const save = useMutation({
    mutationFn: (values: FormValues) =>
      apiRequest<OnboardingState>("/users/me/onboarding", {
        method: "PUT",
        token,
        body: {
          is_new_to_gym: toBoolean(values.is_new_to_gym),
          prefers_uncrowded_hours: toBoolean(values.prefers_uncrowded_hours),
          closer_gym_id: values.closer_gym_id,
          main_goal: toText(values.main_goal),
          training_window: toText(values.training_window),
          days_per_week: toText(values.days_per_week),
          interested_in_classes: toBoolean(values.interested_in_classes),
          interested_in_personal_trainer: toBoolean(values.interested_in_personal_trainer),
        },
      }),
    onSuccess: () => {
      toast.success("Training preferences saved");
      refresh();
      onDone?.();
    },
    onError: (caught) => setError(toUiError(caught)),
  });
  const skip = useMutation({
    mutationFn: () =>
      apiRequest<OnboardingState>("/users/me/onboarding/skip", { method: "POST", token }),
    onSuccess: () => {
      refresh();
      onDone?.();
    },
    onError: (caught) => setError(toUiError(caught)),
  });

  if (onboarding.isLoading || gyms.isLoading) return <LoadingState title="Loading questions" />;
  if (onboarding.isError)
    return (
      <ErrorState
        title={toUiError(onboarding.error).title}
        message={toUiError(onboarding.error).message}
      />
    );
  const gymOptions: Option[] = (gyms.data ?? []).map((gym) => ({ value: gym.id, label: gym.name }));
  const errors = form.formState.errors;
  const busy = save.isPending || skip.isPending;

  return (
    <form
      className="grid gap-4"
      onSubmit={form.handleSubmit((values) => {
        setError(null);
        save.mutate(values);
      })}
      noValidate
    >
      <p className="text-sm text-muted-foreground">
        We use your answers to suggest quiet hours and your closest gym. They are private, optional
        to change later, and never include health information.
      </p>
      {error ? <ErrorState title={error.title} message={error.message} /> : null}
      <RadioGroup
        legend="Are you new to the gym?"
        name="is_new_to_gym"
        options={yesNoOptions}
        register={form.register}
        error={errors.is_new_to_gym?.message}
      />
      <RadioGroup
        legend="Would you like to work out in uncrowded hours?"
        name="prefers_uncrowded_hours"
        options={yesNoOptions}
        register={form.register}
        error={errors.prefers_uncrowded_hours?.message}
      />
      <RadioGroup
        legend="Which location are you closer to?"
        name="closer_gym_id"
        options={gymOptions}
        register={form.register}
        error={errors.closer_gym_id?.message}
      />
      <RadioGroup
        legend="What is your main goal?"
        name="main_goal"
        options={[...goalOptions]}
        register={form.register}
        optional
      />
      <RadioGroup
        legend="When can you usually train?"
        name="training_window"
        options={[...windowOptions]}
        register={form.register}
        optional
      />
      <RadioGroup
        legend="How many days a week?"
        name="days_per_week"
        options={[...daysOptions]}
        register={form.register}
        optional
      />
      <RadioGroup
        legend="Interested in group classes?"
        name="interested_in_classes"
        options={yesNoOptions}
        register={form.register}
        optional
      />
      <RadioGroup
        legend="Interested in a personal trainer?"
        name="interested_in_personal_trainer"
        options={yesNoOptions}
        register={form.register}
        optional
      />
      <div className="flex flex-wrap gap-3">
        <Button type="submit" className="rounded-full" disabled={busy}>
          {save.isPending ? "Saving..." : "Save answers"}
        </Button>
        {showSkip ? (
          <Button
            type="button"
            variant="outline"
            className="rounded-full"
            disabled={busy}
            onClick={() => {
              setError(null);
              skip.mutate();
            }}
          >
            Skip for now
          </Button>
        ) : null}
      </div>
    </form>
  );
}
