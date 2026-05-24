import { LockKeyhole } from "lucide-react";

import { AppFrame } from "@/components/layout/AppFrame";

export function LoginPlaceholderPage() {
  return (
    <AppFrame>
      <main className="mx-auto max-w-3xl px-5 py-12">
        <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
          <LockKeyhole className="size-7 text-primary" aria-hidden />
          <h1 className="mt-4 text-2xl font-bold">Login</h1>
          <p className="mt-3 leading-7 text-muted-foreground">
            Authentication screens will connect here after the backend auth
            module is built.
          </p>
        </div>
      </main>
    </AppFrame>
  );
}
