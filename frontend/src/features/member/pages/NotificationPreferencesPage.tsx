import { useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BellRing, Mail, MessageSquareText, ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { OperationsHeader, Panel } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { queryClient } from "@/lib/queryClient";
import type { NotificationPreference } from "@/types/operations";

export function NotificationPreferencesPage() {
  const { token } = useAuth();
  const preferences = useQuery({ queryKey: ["notifications", "preferences"], queryFn: ({ signal }) => apiRequest<NotificationPreference>("/notifications/preferences/me", { token, signal }) });
  const form = useForm<NotificationPreference>({ defaultValues: { email_enabled: true, in_app_enabled: true, expiry_reminders_enabled: true, broadcasts_enabled: true } });
  useEffect(() => { if (preferences.data) form.reset(preferences.data); }, [form, preferences.data]);
  const save = useMutation({ mutationFn: (values: NotificationPreference) => apiRequest<NotificationPreference>("/notifications/preferences/me", { method: "PATCH", token, body: values }), onSuccess: (data) => { queryClient.setQueryData(["notifications", "preferences"], data); toast.success("Notification preferences saved"); }, onError: (error) => toast.error(toUiError(error).message) });

  return <MemberShell><div className="mx-auto max-w-4xl"><OperationsHeader kicker="Member settings" title="Choose what reaches you." description="Email and in-app channels are stored per member and respected by expiry reminders and broadcasts." />
    {preferences.isLoading ? <LoadingState className="mt-6" title="Loading notification settings" /> : null}
    {preferences.isError ? <ErrorState className="mt-6" title={toUiError(preferences.error).title} message={toUiError(preferences.error).message} /> : null}
    {preferences.data ? <form onSubmit={form.handleSubmit((values) => save.mutate(values))}><Panel title="Channels & categories" detail="Turn off a channel without losing your account notification history."><div className="grid gap-3 p-4"> <PreferenceRow icon={Mail} title="Email delivery" detail="Development emails are logged locally." field="email_enabled" register={form.register} /><PreferenceRow icon={MessageSquareText} title="In-app notifications" detail="Show records in your notification inbox." field="in_app_enabled" register={form.register} /><PreferenceRow icon={BellRing} title="Expiry reminders" detail="Receive reminders 7, 3 and 1 day before expiry." field="expiry_reminders_enabled" register={form.register} /><PreferenceRow icon={ShieldCheck} title="Gym broadcasts" detail="Show active operational announcements." field="broadcasts_enabled" register={form.register} /></div><div className="flex justify-end border-t border-border p-4"><Button type="submit" disabled={save.isPending}>{save.isPending ? "Saving..." : "Save preferences"}</Button></div></Panel></form> : null}
  </div></MemberShell>;
}

function PreferenceRow({ icon: Icon, title, detail, field, register }: { icon: typeof Mail; title: string; detail: string; field: keyof NotificationPreference; register: ReturnType<typeof useForm<NotificationPreference>>["register"] }) { return <label className="flex cursor-pointer items-center gap-4 rounded-xl border border-border p-4 transition-colors hover:bg-muted/40"><span className="grid size-10 place-items-center rounded-xl bg-secondary"><Icon className="size-5" /></span><span className="min-w-0 flex-1"><strong className="block text-sm">{title}</strong><small className="mt-1 block text-xs text-muted-foreground">{detail}</small></span><input className="size-5 accent-[hsl(var(--primary))]" type="checkbox" {...register(field)} /></label>; }
