import { zodResolver } from "@hookform/resolvers/zod";
import { MailCheck } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { ErrorState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { apiRequest } from "@/lib/apiClient";
import { toUiError, type UiError } from "@/lib/apiErrors";

const schema = z.object({
  email: z.string().email(),
});

type ForgotPasswordForm = z.infer<typeof schema>;

export function ForgotPasswordPage() {
  const [error, setError] = useState<UiError | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const form = useForm<ForgotPasswordForm>({
    resolver: zodResolver(schema),
    defaultValues: { email: "" },
  });

  async function onSubmit(values: ForgotPasswordForm) {
    setError(null);
    setSuccess(null);
    try {
      const response = await apiRequest<{ message: string }>(
        "/auth/forgot-password",
        {
          method: "POST",
          body: values,
        },
      );
      setSuccess(response.message);
      form.reset();
    } catch (caught) {
      setError(toUiError(caught));
    }
  }

  return (
    <AppFrame>
      <main className="mx-auto max-w-xl px-5 py-10">
        <section className="rounded-lg border border-border bg-card p-6 shadow-sm">
          <MailCheck className="size-8 text-primary" aria-hidden />
          <h1 className="mt-4 text-3xl font-bold">Forgot Password</h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Enter your account email. The response stays neutral for privacy.
          </p>

          {success ? (
            <div className="mt-5 rounded-lg border border-secondary/30 bg-secondary/10 p-4 text-sm leading-6">
              {success} In local development, check backend logs for the reset
              link.
            </div>
          ) : null}

          {error ? (
            <ErrorState
              className="mt-5"
              title={error.title}
              message={error.message}
            />
          ) : null}

          <form className="mt-6 space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
            <Field>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
              <FieldError message={form.formState.errors.email?.message} />
            </Field>
            <Button
              type="submit"
              className="w-full"
              disabled={form.formState.isSubmitting}
            >
              {form.formState.isSubmitting ? "Preparing link..." : "Request reset link"}
            </Button>
          </form>

          <ButtonLink asChild variant="ghost" className="mt-4 w-full">
            <Link to="/login">Back to login</Link>
          </ButtonLink>
        </section>
      </main>
    </AppFrame>
  );
}
