import { zodResolver } from "@hookform/resolvers/zod";
import { Bell, ChevronRight, CircleUserRound, KeyRound, LockKeyhole, Palette, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError, type UiError } from "@/lib/apiErrors";
import { queryClient } from "@/lib/queryClient";
import type { User } from "@/types/api";

const schema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters."),
  phone: z.string().min(7, "Phone number is too short."),
  current_password: z.string().optional(),
  new_password: z.string().optional(),
}).refine((values) => !values.new_password || values.new_password.length >= 8, { message: "New password must be at least 8 characters.", path: ["new_password"] }).refine((values) => !values.new_password || values.current_password, { message: "Current password is required.", path: ["current_password"] });

type ProfileForm = z.infer<typeof schema>;
const profileRows = [
  { label: "Personal information", detail: "Name, phone and protected email", icon: CircleUserRound, connected: true, href: "#personal-information" },
  { label: "Account security", detail: "Password changes are connected", icon: LockKeyhole, connected: true, href: "#account-security" },
  { label: "Personalization profile", detail: "Planned after Day 20", icon: Palette, connected: false },
  { label: "Notification preferences", detail: "Email, in-app, reminders, and broadcasts", icon: Bell, connected: true, href: "/app/notifications/preferences" },
];

export function ProfileSettingsPage() {
  const { token, refreshUser } = useAuth();
  const [error, setError] = useState<UiError | null>(null);
  const profile = useQuery({ queryKey: ["profile"], enabled: Boolean(token), queryFn: ({ signal }) => apiRequest<User>("/users/me", { token, signal }) });
  const form = useForm<ProfileForm>({ resolver: zodResolver(schema), defaultValues: { name: "", phone: "", current_password: "", new_password: "" } });

  useEffect(() => {
    if (!profile.data) return;
    form.reset({ name: profile.data.name, phone: profile.data.phone, current_password: "", new_password: "" });
  }, [form, profile.data]);

  const updateProfile = useMutation({
    mutationFn: (values: ProfileForm) => apiRequest<User>("/users/me", { method: "PATCH", token, body: { name: values.name, phone: values.phone, current_password: values.current_password || undefined, new_password: values.new_password || undefined } }),
    onSuccess: async (updated, values) => {
      queryClient.setQueryData(["profile"], updated);
      await refreshUser();
      form.reset({ name: values.name, phone: values.phone, current_password: "", new_password: "" });
      toast.success("Profile updated");
    },
    onError: (caught) => setError(toUiError(caught)),
  });

  function onSubmit(values: ProfileForm) { setError(null); updateProfile.mutate(values); }

  return <MemberShell>
    <div className="mx-auto max-w-5xl">
      <p className="page-kicker">Member profile</p><h1 className="page-title">Account & security.</h1><p className="page-description">This profile follows the Figma settings hierarchy while keeping email edit restrictions and password verification visible.</p>
      {profile.isLoading ? <LoadingState className="mt-7" title="Loading profile" /> : null}
      {profile.isError ? <ErrorState className="mt-7" title={toUiError(profile.error).title} message={toUiError(profile.error).message} /> : null}
      {profile.data ? <div className="mt-8 grid gap-6 lg:grid-cols-[0.76fr_1.24fr]">
        <aside className="surface-card h-fit overflow-hidden">
          <div className="bg-primary p-6 text-primary-foreground"><span className="grid size-14 place-items-center rounded-2xl bg-secondary text-xl font-extrabold text-foreground">{profile.data.name.slice(0, 1).toUpperCase()}</span><p className="mt-5 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">{profile.data.name}</p><p className="mt-2 text-xs text-primary-foreground/65">{profile.data.tier} membership · {profile.data.is_email_verified ? "Verified" : "Verification pending"}</p></div>
          <nav className="p-3" aria-label="Profile settings">
            {profileRows.map((row) => {
              const Icon = row.icon;
              const content = <><span className={`grid size-9 place-items-center rounded-lg ${row.connected ? "bg-secondary text-foreground" : "bg-muted text-muted-foreground"}`}><Icon className="size-4" aria-hidden /></span><span className="min-w-0 flex-1"><strong className="block text-xs">{row.label}</strong><small className="block pt-0.5 text-[11px] text-muted-foreground">{row.detail}</small></span>{row.connected ? <ChevronRight className="size-4 text-muted-foreground" aria-hidden /> : <small className="rounded-full bg-muted px-2 py-1 text-[9px] font-extrabold uppercase text-muted-foreground">Unavailable</small>}</>;
              return row.href ? <Link className="flex items-center gap-3 rounded-xl p-3 hover:bg-muted/40" to={row.href} key={row.label}>{content}</Link> : <div className="flex items-center gap-3 rounded-xl p-3" key={row.label}>{content}</div>;
            })}
          </nav>
        </aside>
        <section id="personal-information" className="surface-card p-6 sm:p-8"><div className="flex items-start gap-3"><span className="grid size-10 place-items-center rounded-xl bg-secondary text-foreground"><ShieldCheck className="size-5" aria-hidden /></span><div><h2 className="font-['Barlow_Condensed'] text-3xl font-bold uppercase leading-none">Personal information</h2><p className="mt-1 text-sm text-muted-foreground">Update your details and, if needed, set a new password.</p></div></div>{error ? <ErrorState className="mt-6" title={error.title} message={error.message} /> : null}<form className="mt-7 grid gap-5 sm:grid-cols-2" onSubmit={form.handleSubmit(onSubmit)}><Field><Label htmlFor="name">Full name</Label><Input id="name" autoComplete="name" {...form.register("name")} /><FieldError message={form.formState.errors.name?.message} /></Field><Field><Label htmlFor="phone">Phone number</Label><Input id="phone" autoComplete="tel" {...form.register("phone")} /><FieldError message={form.formState.errors.phone?.message} /></Field><Field className="sm:col-span-2"><Label htmlFor="email">Email address</Label><Input id="email" value={profile.data.email} disabled readOnly /><p className="text-xs leading-5 text-muted-foreground">Email edits are blocked until the re-verification workflow is implemented.</p></Field><div id="account-security" className="sm:col-span-2"><div className="mb-3 flex items-center gap-2 border-t border-border pt-6"><KeyRound className="size-4 text-primary" aria-hidden /><h3 className="text-xl font-bold">Password change</h3></div><p className="mb-4 text-xs leading-5 text-muted-foreground">Leave both fields empty to keep your current password.</p><div className="grid gap-5 sm:grid-cols-2"><Field><Label htmlFor="current_password">Current password</Label><Input id="current_password" type="password" autoComplete="current-password" {...form.register("current_password")} /><FieldError message={form.formState.errors.current_password?.message} /></Field><Field><Label htmlFor="new_password">New password</Label><Input id="new_password" type="password" autoComplete="new-password" {...form.register("new_password")} /><FieldError message={form.formState.errors.new_password?.message} /></Field></div></div><Button type="submit" className="rounded-full sm:w-fit" disabled={updateProfile.isPending}>{updateProfile.isPending ? "Saving changes..." : "Save profile"}</Button></form></section>
      </div> : null}
    </div>
  </MemberShell>;
}
