import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, KeyRound } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { ErrorState } from "@/components/common/FeedbackState";
import { AuthShell } from "@/components/layout/AuthShell";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { apiRequest } from "@/lib/apiClient";
import { toUiError, type UiError } from "@/lib/apiErrors";

const schema = z.object({ new_password: z.string().min(8, "Password must be at least 8 characters."), confirm_password: z.string().min(8, "Confirm your password.") }).refine((values) => values.new_password === values.confirm_password, { message: "Passwords do not match.", path: ["confirm_password"] });
type ResetPasswordForm = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [error, setError] = useState<UiError | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const form = useForm<ResetPasswordForm>({ resolver: zodResolver(schema), defaultValues: { new_password: "", confirm_password: "" } });

  async function onSubmit(values: ResetPasswordForm) {
    if (!token) {
      setError({ code: "INVALID_RESET_TOKEN", title: "Invalid reset token", message: "The reset link is missing its token. Request a new password reset link and open it in full." });
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      const response = await apiRequest<{ message: string }>("/auth/reset-password", { method: "POST", body: { token, new_password: values.new_password } });
      setSuccess(response.message);
      form.reset();
    } catch (caught) {
      setError(toUiError(caught));
    }
  }

  return (
    <AuthShell eyebrow="Secure reset" title={<>Choose a new<br /><span className="text-secondary">starting point.</span></>} description="This page keeps the token from the reset URL and sends it with your new password to the backend." detail="Reset links are one-time use. Invalid or expired links return the backend error without masking it.">
      <section className="form-card p-6 sm:p-8">
        <span className="grid size-11 place-items-center rounded-xl bg-secondary text-foreground"><KeyRound className="size-5" aria-hidden /></span>
        <h2 className="mt-5 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">Set a new password</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">Create a password with at least eight characters.</p>
        {success ? <div className="mt-5 rounded-2xl border border-secondary/50 bg-secondary/15 p-4 text-sm leading-6"><strong className="block text-foreground">Password updated.</strong><span className="text-muted-foreground">{success}</span><Link className="mt-4 inline-flex items-center gap-2 font-extrabold text-primary underline-offset-4 hover:underline" to="/login">Back to login <ArrowRight className="size-4" aria-hidden /></Link></div> : null}
        {error ? <ErrorState className="mt-5" title={error.title} message={error.message} /> : null}
        {!success ? <form className="mt-6 space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <Field><Label htmlFor="new_password">New password</Label><Input id="new_password" type="password" autoComplete="new-password" {...form.register("new_password")} /><FieldError message={form.formState.errors.new_password?.message} /></Field>
          <Field><Label htmlFor="confirm_password">Confirm password</Label><Input id="confirm_password" type="password" autoComplete="new-password" {...form.register("confirm_password")} /><FieldError message={form.formState.errors.confirm_password?.message} /></Field>
          <Button type="submit" className="w-full rounded-full" disabled={form.formState.isSubmitting}>{form.formState.isSubmitting ? "Saving..." : <>Save new password <ArrowRight className="size-4" aria-hidden /></>}</Button>
        </form> : null}
      </section>
    </AuthShell>
  );
}
