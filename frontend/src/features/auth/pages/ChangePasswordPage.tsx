import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { ErrorState } from "@/components/common/FeedbackState";
import { AuthShell } from "@/components/layout/AuthShell";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { workspacePathForRole } from "@/features/auth/workspace";
import { apiRequest } from "@/lib/apiClient";
import { applyApiFieldErrors, toUiError, type UiError } from "@/lib/apiErrors";
import type { User } from "@/types/api";

const schema = z.object({
  current_password: z.string().min(1, "Enter the temporary password."),
  new_password: z.string().min(8, "Use at least 8 characters."),
  confirm_password: z.string().min(1, "Confirm the new password."),
}).refine((values) => values.new_password === values.confirm_password, {
  path: ["confirm_password"],
  message: "Passwords do not match.",
});

type PasswordForm = z.infer<typeof schema>;

export function ChangePasswordPage() {
  const { token, user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<UiError | null>(null);
  const form = useForm<PasswordForm>({
    resolver: zodResolver(schema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  async function onSubmit(values: PasswordForm) {
    setError(null);
    try {
      await apiRequest<User>("/users/me", {
        method: "PATCH",
        token,
        body: { current_password: values.current_password, new_password: values.new_password },
      });
      await refreshUser();
      toast.success("Password changed");
      navigate(workspacePathForRole(user!.role), { replace: true });
    } catch (caught) {
      if (!applyApiFieldErrors(caught, form.setError, ["current_password", "new_password"])) {
        setError(toUiError(caught));
      }
    }
  }

  return <AuthShell eyebrow="Account security" title={<>Set your private<br /><span className="text-secondary">password.</span></>} description="Temporary workforce credentials must be replaced before other YPGym tools become available." detail="Your manager cannot retrieve the temporary password after account creation.">
    <section className="form-card p-6 sm:p-8">
      <span className="grid size-11 place-items-center rounded-xl bg-secondary text-foreground"><KeyRound className="size-5" aria-hidden /></span>
      <h1 className="mt-5 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">Change password</h1>
      {error ? <ErrorState className="mt-5" title={error.title} message={error.message} /> : null}
      <form className="mt-6 grid gap-4" onSubmit={form.handleSubmit(onSubmit)}>
        <Field><Label htmlFor="current_password">Temporary or current password</Label><Input id="current_password" type="password" autoComplete="current-password" {...form.register("current_password")} /><FieldError message={form.formState.errors.current_password?.message} /></Field>
        <Field><Label htmlFor="new_password">New password</Label><Input id="new_password" type="password" autoComplete="new-password" {...form.register("new_password")} /><FieldError message={form.formState.errors.new_password?.message} /></Field>
        <Field><Label htmlFor="confirm_password">Confirm new password</Label><Input id="confirm_password" type="password" autoComplete="new-password" {...form.register("confirm_password")} /><FieldError message={form.formState.errors.confirm_password?.message} /></Field>
        <Button type="submit" className="mt-2 w-full rounded-full" disabled={form.formState.isSubmitting}>{form.formState.isSubmitting ? "Saving..." : "Set password and continue"}</Button>
      </form>
    </section>
  </AuthShell>;
}
