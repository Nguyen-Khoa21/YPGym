import { zodResolver } from "@hookform/resolvers/zod";
import { LogIn } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { ErrorState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { toUiError, type UiError } from "@/lib/apiErrors";
import type { User } from "@/types/api";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1, "Password is required."),
});

type LoginForm = z.infer<typeof schema>;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<UiError | null>(null);

  const form = useForm<LoginForm>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: LoginForm) {
    setError(null);
    try {
      const user = await login(values.email, values.password);
      const fallback = destinationForRole(user);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from || fallback, { replace: true });
    } catch (caught) {
      setError(toUiError(caught));
    }
  }

  return (
    <AppFrame>
      <main className="mx-auto grid max-w-6xl gap-8 px-5 py-10 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
        <section className="space-y-4">
          <p className="text-sm font-semibold uppercase tracking-wide text-primary">
            Member access
          </p>
          <h1 className="text-4xl font-bold leading-tight md:text-5xl">
            Login to YPGym
          </h1>
          <p className="max-w-xl text-base leading-7 text-muted-foreground">
            Continue to billing, membership renewal, invoices, and profile
            settings from the member workspace.
          </p>
        </section>

        <section className="rounded-lg border border-border bg-card p-6 shadow-sm">
          <div className="mb-6 flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-md bg-primary/10 text-primary">
              <LogIn className="size-5" aria-hidden />
            </span>
            <div>
              <h2 className="text-xl font-bold">Welcome back</h2>
              <p className="text-sm text-muted-foreground">
                Use your verified email and password.
              </p>
            </div>
          </div>

          {error ? (
            <ErrorState
              className="mb-5"
              title={error.title}
              message={error.message}
            />
          ) : null}

          <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
            <Field>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
              <FieldError message={form.formState.errors.email?.message} />
            </Field>

            <Field>
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...form.register("password")}
              />
              <FieldError message={form.formState.errors.password?.message} />
            </Field>

            <Button
              type="submit"
              className="w-full"
              disabled={form.formState.isSubmitting}
            >
              {form.formState.isSubmitting ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          <div className="mt-5 flex flex-wrap justify-between gap-3 text-sm">
            <Link className="font-semibold text-primary" to="/forgot-password">
              Forgot password?
            </Link>
            <Link className="font-semibold text-primary" to="/register">
              Create an account
            </Link>
          </div>
        </section>
      </main>
    </AppFrame>
  );
}

function destinationForRole(user: User) {
  if (["admin", "manager", "staff"].includes(user.role)) {
    return "/admin";
  }
  if (user.role === "pt") {
    return "/pt";
  }
  return "/member";
}
