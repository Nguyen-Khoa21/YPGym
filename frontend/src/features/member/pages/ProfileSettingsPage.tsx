import { zodResolver } from "@hookform/resolvers/zod";
import { ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { ErrorState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError, type UiError } from "@/lib/apiErrors";
import type { User } from "@/types/api";

const schema = z
  .object({
    name: z.string().min(2, "Name must be at least 2 characters."),
    phone: z.string().min(7, "Phone number is too short."),
    current_password: z.string().optional(),
    new_password: z.string().optional(),
  })
  .refine(
    (values) => !values.new_password || values.new_password.length >= 8,
    {
      message: "New password must be at least 8 characters.",
      path: ["new_password"],
    },
  )
  .refine((values) => !values.new_password || values.current_password, {
    message: "Current password is required.",
    path: ["current_password"],
  });

type ProfileForm = z.infer<typeof schema>;

export function ProfileSettingsPage() {
  const { user, token, refreshUser } = useAuth();
  const [error, setError] = useState<UiError | null>(null);
  const form = useForm<ProfileForm>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: user?.name ?? "",
      phone: user?.phone ?? "",
      current_password: "",
      new_password: "",
    },
  });

  useEffect(() => {
    form.reset({
      name: user?.name ?? "",
      phone: user?.phone ?? "",
      current_password: "",
      new_password: "",
    });
  }, [form, user]);

  async function onSubmit(values: ProfileForm) {
    setError(null);
    const body = {
      name: values.name,
      phone: values.phone,
      current_password: values.current_password || undefined,
      new_password: values.new_password || undefined,
    };

    try {
      await apiRequest<User>("/users/me", {
        method: "PATCH",
        token,
        body,
      });
      await refreshUser();
      toast.success("Profile updated");
      form.reset({
        name: values.name,
        phone: values.phone,
        current_password: "",
        new_password: "",
      });
    } catch (caught) {
      setError(toUiError(caught));
    }
  }

  return (
    <AppFrame>
      <main className="mx-auto max-w-4xl px-5 py-10">
        <div className="mb-6">
          <p className="text-sm font-semibold uppercase tracking-wide text-primary">
            Account security
          </p>
          <h1 className="mt-2 text-3xl font-bold">Profile Settings</h1>
          <p className="mt-2 text-muted-foreground">
            Keep member contact details current. Password changes require your
            existing password.
          </p>
        </div>

        <section className="rounded-lg border border-border bg-card p-6 shadow-sm">
          <div className="mb-6 flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-md bg-secondary/10 text-secondary">
              <ShieldCheck className="size-5" aria-hidden />
            </span>
            <div>
              <h2 className="text-xl font-bold">{user?.name}</h2>
              <p className="text-sm text-muted-foreground">
                {user?.email} · {user?.tier} tier
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

          <form className="grid gap-4 md:grid-cols-2" onSubmit={form.handleSubmit(onSubmit)}>
            <Field>
              <Label htmlFor="name">Name</Label>
              <Input id="name" autoComplete="name" {...form.register("name")} />
              <FieldError message={form.formState.errors.name?.message} />
            </Field>
            <Field>
              <Label htmlFor="phone">Phone</Label>
              <Input id="phone" autoComplete="tel" {...form.register("phone")} />
              <FieldError message={form.formState.errors.phone?.message} />
            </Field>
            <Field>
              <Label htmlFor="email">Email</Label>
              <Input id="email" value={user?.email ?? ""} disabled readOnly />
              <p className="text-xs leading-5 text-muted-foreground">
                Email changes are reserved for the re-verification workflow.
              </p>
            </Field>
            <div className="hidden md:block" />
            <Field>
              <Label htmlFor="current_password">Current password</Label>
              <Input
                id="current_password"
                type="password"
                autoComplete="current-password"
                {...form.register("current_password")}
              />
              <FieldError message={form.formState.errors.current_password?.message} />
            </Field>
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
            <div className="md:col-span-2">
              <Button
                type="submit"
                disabled={form.formState.isSubmitting}
                className="w-full md:w-auto"
              >
                {form.formState.isSubmitting ? "Saving..." : "Save profile"}
              </Button>
            </div>
          </form>
        </section>
      </main>
    </AppFrame>
  );
}
