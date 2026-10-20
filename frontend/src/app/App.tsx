import { Suspense } from "react";
import { RouterProvider } from "react-router-dom";

import { AppProviders } from "@/app/providers";
import { router } from "@/app/router";
import { LoadingState } from "@/components/common/FeedbackState";

export function App() {
  return (
    <AppProviders>
      <Suspense fallback={<RouteLoadingFallback />}>
        <RouterProvider router={router} />
      </Suspense>
    </AppProviders>
  );
}

function RouteLoadingFallback() {
  return (
    <main
      className="grid min-h-screen place-items-center bg-background px-5 py-10 text-foreground"
      id="main-content"
    >
      <div className="w-full max-w-3xl">
        <LoadingState
          title="Loading page"
          message="Please wait while this part of YPGym is loaded."
        />
      </div>
    </main>
  );
}
