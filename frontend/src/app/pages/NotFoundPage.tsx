import { Link } from "react-router-dom";

import { AppFrame } from "@/components/layout/AppFrame";

export function NotFoundPage() {
  return (
    <AppFrame>
      <main className="mx-auto max-w-3xl px-5 py-16">
        <p className="text-sm font-semibold text-primary">404</p>
        <h1 className="mt-3 text-3xl font-bold">Page not found</h1>
        <p className="mt-3 text-muted-foreground">
          The requested YPGym route is not available.
        </p>
        <Link
          to="/"
          className="mt-6 inline-flex rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          Back Home
        </Link>
      </main>
    </AppFrame>
  );
}
