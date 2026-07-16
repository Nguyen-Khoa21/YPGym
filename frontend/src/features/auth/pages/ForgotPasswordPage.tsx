import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, MailCheck } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { ErrorState } from "@/components/common/FeedbackState";
import { AuthShell } from "@/components/layout/AuthShell";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { apiRequest } from "@/lib/apiClient";
import { toUiError, type UiError } from "@/lib/apiErrors";

const schema = z.object({ email: z.string().email("Enter a valid email address.") });
type ForgotPasswordForm = z.infer<typeof schema>;

export function ForgotPasswordPage() {
  const [error, setError] = useState<UiError | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const form = useForm<ForgotPasswordForm>({ resolver: zodResolver(schema), defaultValues: { email: "" } });

  async function onSubmit(values: ForgotPasswordForm) {
    setError(null);
    setSuccess(null);
    try {
      const response = await apiRequest<{ message: string }>("/auth/forgot-password", { method: "POST", body: values });
      setSuccess(response.message);
      form.reset();
    } catch (caught) {
      setError(toUiError(caught));
    }
  }

  return (
    <AuthShell eyebrow="Account recovery" title={<>Reset, then<br /><span className="text-secondary">move forward.</span></>} description="Request a one-time password reset link without revealing whether an account exists for that email." detail="The reset request uses the same neutral server response for every email address.">
      <section className="form-card p-6 sm:p-8">
        <span className="grid size-11 place-items-center rounded-xl bg-secondary text-foreground"><MailCheck className="size-5" aria-hidden /></span>
        <h2 className="mt-5 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">Forgot password?</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">Enter your account email and we will prepare a reset link if appropriate.</p>
        {success ? <div className="mt-5 rounded-2xl border border-secondary/50 bg-secondary/15 p-4 text-sm leading-6"><strong className="block text-foreground">Request received.</strong><span className="text-muted-foreground">{success} In development, check the backend logs for the reset link.</span></div> : null}
        {error ? <ErrorState className="mt-5" title={error.title} message={error.message} /> : null}
        {!success ? <form className="mt-6 space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <Field><Label htmlFor="email">Email address</Label><Input id="email" type="email" autoComplete="email" placeholder="you@example.com" {...form.register("email")} /><FieldError message={form.formState.errors.email?.message} /></Field>
          <Button type="submit" className="w-full rounded-full" disabled={form.formState.isSubmitting}>{form.formState.isSubmitting ? "Preparing link..." : <>Request reset link <ArrowRight className="size-4" aria-hidden /></>}</Button>
        </form> : null}
        <p className="mt-6 text-center text-sm text-muted-foreground"><Link className="font-extrabold text-primary underline-offset-4 hover:underline" to="/login">Back to login</Link></p>
      </section>
    </AuthShell>
  );
}
