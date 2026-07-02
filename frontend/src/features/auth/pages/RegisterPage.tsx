import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, UserPlus } from "lucide-react";
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
import type { User } from "@/types/api";

const schema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters."),
  email: z.string().email(),
  phone: z.string().min(7, "Phone number is too short."),
  password: z.string().min(8, "Password must be at least 8 characters."),
});

type RegisterForm = z.infer<typeof schema>;

type RegisterResponse = {
  message: string;
  user: User;
};

export function RegisterPage() {
  const [error, setError] = useState<UiError | null>(null);
  const [registered, setRegistered] = useState<RegisterResponse | null>(null);
  const form = useForm<RegisterForm>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", email: "", phone: "", password: "" },
  });

  async function onSubmit(values: RegisterForm) {
    setError(null);
    setRegistered(null);
    try {
      const response = await apiRequest<RegisterResponse>("/auth/register", {
        method: "POST",
        body: values,
      });
      setRegistered(response);
      form.reset();
    } catch (caught) {
      setError(toUiError(caught));
    }
  }

  return (
    <AppFrame>
      <main className="mx-auto grid max-w-6xl gap-8 px-5 py-10 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
        <section className="space-y-4">
          <p className="text-sm font-semibold uppercase tracking-wide text-primary">
            Start training
          </p>
          <h1 className="text-4xl font-bold leading-tight md:text-5xl">
            Register for YPGym
          </h1>
          <p className="max-w-xl text-base leading-7 text-muted-foreground">
            Create a member account, verify email, then choose a membership
            plan that fits your schedule.
          </p>
        </section>

        <section className="rounded-lg border border-border bg-card p-6 shadow-sm">
          <div className="mb-6 flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-md bg-secondary/10 text-secondary">
              <UserPlus className="size-5" aria-hidden />
            </span>
            <div>
              <h2 className="text-xl font-bold">Member details</h2>
              <p className="text-sm text-muted-foreground">
                Email and phone must be unique.
              </p>
            </div>
          </div>

          {registered ? (
            <div className="rounded-lg border border-secondary/30 bg-secondary/10 p-5">
              <CheckCircle2 className="size-6 text-secondary" aria-hidden />
              <h2 className="mt-3 text-lg font-bold">Check your verification link</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {registered.message} In local development, the verification
                link is written to the backend logs.
              </p>
              <ButtonLink asChild className="mt-4">
                <Link to="/login">Go to login</Link>
              </ButtonLink>
            </div>
          ) : null}

          {error ? (
            <ErrorState
              className="mb-5"
              title={error.title}
              message={error.message}
            />
          ) : null}

          <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
            <Field>
              <Label htmlFor="name">Name</Label>
              <Input id="name" autoComplete="name" {...form.register("name")} />
              <FieldError message={form.formState.errors.name?.message} />
            </Field>
            <Field>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
              <FieldError message={form.formState.errors.email?.message} />
            </Field>
            <Field>
              <Label htmlFor="phone">Phone</Label>
              <Input id="phone" autoComplete="tel" {...form.register("phone")} />
              <FieldError message={form.formState.errors.phone?.message} />
            </Field>
            <Field>
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                {...form.register("password")}
              />
              <FieldError message={form.formState.errors.password?.message} />
            </Field>
            <Button
              type="submit"
              className="w-full"
              disabled={form.formState.isSubmitting}
            >
              {form.formState.isSubmitting ? "Creating account..." : "Create account"}
            </Button>
          </form>
        </section>
      </main>
    </AppFrame>
  );
}
