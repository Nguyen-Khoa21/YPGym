import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, BadgeCheck, UserPlus } from "lucide-react";
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
import type { User } from "@/types/api";

const schema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters."),
  email: z.string().email("Enter a valid email address."),
  phone: z.string().min(7, "Phone number is too short."),
  password: z.string().min(8, "Password must be at least 8 characters."),
});

type RegisterForm = z.infer<typeof schema>;
type RegisterResponse = { message: string; user: User };

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
      const response = await apiRequest<RegisterResponse>("/auth/register", { method: "POST", body: values });
      setRegistered(response);
      form.reset();
    } catch (caught) {
      setError(toUiError(caught));
    }
  }

  return (
    <AuthShell
      eyebrow="New member"
      title={<>Find your<br /><span className="text-secondary">pace.</span></>}
      description="Start with a secure member account. Verify your email, then select a plan configured by the gym."
      detail="Your email and phone are checked against the real account records before a profile is created."
    >
      <section className="form-card p-6 sm:p-8">
        <span className="grid size-11 place-items-center rounded-xl bg-secondary text-foreground"><UserPlus className="size-5" aria-hidden /></span>
        <h2 className="mt-5 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">Create account</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">Your email and phone number must be unique.</p>
        {registered ? <div className="mt-5 rounded-2xl border border-secondary/50 bg-secondary/15 p-4"><BadgeCheck className="size-5 text-primary" aria-hidden /><h3 className="mt-3 text-xl font-bold">Check your verification link</h3><p className="mt-1 text-sm leading-6 text-muted-foreground">{registered.message} Check the email inbox configured for this environment.</p><Link className="mt-4 inline-flex items-center gap-2 text-sm font-extrabold text-primary underline-offset-4 hover:underline" to="/login">Go to login <ArrowRight className="size-4" aria-hidden /></Link></div> : null}
        {error ? <ErrorState className="mt-5" title={error.title} message={error.message} /> : null}
        {!registered ? <form className="mt-6 grid gap-4 sm:grid-cols-2" onSubmit={form.handleSubmit(onSubmit)}>
          <Field className="sm:col-span-2"><Label htmlFor="name">Full name</Label><Input id="name" autoComplete="name" {...form.register("name")} /><FieldError message={form.formState.errors.name?.message} /></Field>
          <Field className="sm:col-span-2"><Label htmlFor="email">Email address</Label><Input id="email" type="email" autoComplete="email" placeholder="you@example.com" {...form.register("email")} /><FieldError message={form.formState.errors.email?.message} /></Field>
          <Field><Label htmlFor="phone">Phone number</Label><Input id="phone" autoComplete="tel" {...form.register("phone")} /><FieldError message={form.formState.errors.phone?.message} /></Field>
          <Field><Label htmlFor="password">Password</Label><Input id="password" type="password" autoComplete="new-password" {...form.register("password")} /><FieldError message={form.formState.errors.password?.message} /></Field>
          <Button type="submit" className="mt-2 w-full rounded-full sm:col-span-2" disabled={form.formState.isSubmitting}>{form.formState.isSubmitting ? "Creating account..." : <>Create account <ArrowRight className="size-4" aria-hidden /></>}</Button>
        </form> : null}
        <p className="mt-6 text-center text-sm text-muted-foreground">Already registered? <Link className="font-extrabold text-primary underline-offset-4 hover:underline" to="/login">Log in</Link></p>
      </section>
    </AuthShell>
  );
}
