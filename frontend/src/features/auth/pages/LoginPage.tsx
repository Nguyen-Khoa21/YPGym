import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, KeyRound } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { ErrorState } from "@/components/common/FeedbackState";
import { AuthShell } from "@/components/layout/AuthShell";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { workspacePathForRole } from "@/features/auth/workspace";
import { toUiError, type UiError } from "@/lib/apiErrors";

const schema = z.object({
  email: z.string().email("Enter a valid email address."),
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
      const fallback = workspacePathForRole(user.role);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(user.role === "member" && from ? from : fallback, { replace: true });
    } catch (caught) {
      setError(toUiError(caught));
    }
  }

  return (
    <AuthShell
      eyebrow="Member access"
      title={<>Back to your<br /><span className="text-secondary">training.</span></>}
      description="Sign in to manage your membership, update your profile and keep your invoices in one place."
      detail="Protected destinations only render after the current session has been resolved."
    >
      <section className="form-card p-6 sm:p-8">
        <span className="grid size-11 place-items-center rounded-xl bg-secondary text-foreground"><KeyRound className="size-5" aria-hidden /></span>
        <h2 className="mt-5 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">Welcome back</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">Use your verified YPGym email and password.</p>
        {error ? <ErrorState className="mt-5" title={error.title} message={error.message} /> : null}
        <form className="mt-6 space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <Field>
            <Label htmlFor="email">Email address</Label>
            <Input id="email" type="email" autoComplete="email" placeholder="you@example.com" {...form.register("email")} />
            <FieldError message={form.formState.errors.email?.message} />
          </Field>
          <Field>
            <div className="flex items-center justify-between gap-3"><Label htmlFor="password">Password</Label><Link className="text-xs font-extrabold text-primary underline-offset-4 hover:underline" to="/forgot-password">Forgot password?</Link></div>
            <Input id="password" type="password" autoComplete="current-password" {...form.register("password")} />
            <FieldError message={form.formState.errors.password?.message} />
          </Field>
          <Button type="submit" className="mt-2 w-full rounded-full" disabled={form.formState.isSubmitting}>
            {form.formState.isSubmitting ? "Signing in..." : <>Sign in <ArrowRight className="size-4" aria-hidden /></>}
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-muted-foreground">New to YPGym? <Link className="font-extrabold text-primary underline-offset-4 hover:underline" to="/register">Create an account</Link></p>
      </section>
    </AuthShell>
  );
}
