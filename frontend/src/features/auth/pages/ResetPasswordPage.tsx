import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { ErrorState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { apiRequest } from "@/lib/apiClient";
import { toUiError, type UiError } from "@/lib/apiErrors";

const schema = z
  .object({
    new_password: z.string().min(8, "Password must be at least 8 characters."),
    confirm_password: z.string().min(8, "Confirm your password."),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });

type ResetPasswordForm = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [error, setError] = useState<UiError | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const form = useForm<ResetPasswordForm>({
    resolver: zodResolver(schema),
    defaultValues: { new_password: "", confirm_password: "" },
  });

  async function onSubmit(values: ResetPasswordForm) {
    if (!token) {
      setError({
        code: "INVALID_RESET_TOKEN",
        title: "Invalid Reset Token",
        message: "The reset link is missing a token.",
      });
      return;
    }

    setError(null);
    setSuccess(null);
    try {
      const response = await apiRequest<{ message: string }>("/auth/reset-password", {
        method: "POST",
        body: { token, new_password: values.new_password },
      });
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
          <KeyRound className="size-8 text-primary" aria-hidden />
          <h1 className="mt-4 text-3xl font-bold">Reset Password</h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Set a new password using the reset link from your email.
          </p>

          {success ? (
            <div className="mt-5 rounded-lg border border-secondary/30 bg-secondary/10 p-4 text-sm leading-6">
              {success}
              <ButtonLink asChild className="mt-4 w-full">
                <Link to="/login">Back to login</Link>
              </ButtonLink>
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
              <Label htmlFor="new_password">New password</Label>
              <Input
                id="new_password"
                type="password"
                autoComplete="new-password"
                {...form.register("new_password")}
              />
              <FieldError message={form.formState.errors.new_password?.message} />
            </Field>
            <Field>
              <Label htmlFor="confirm_password">Confirm password</Label>
              <Input
                id="confirm_password"
                type="password"
                autoComplete="new-password"
                {...form.register("confirm_password")}
              />
              <FieldError message={form.formState.errors.confirm_password?.message} />
            </Field>
            <Button
              type="submit"
              className="w-full"
              disabled={form.formState.isSubmitting || Boolean(success)}
            >
              {form.formState.isSubmitting ? "Saving..." : "Save new password"}
            </Button>
          </form>
        </section>
      </main>
    </AppFrame>
  );
}
