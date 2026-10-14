import { Component, createElement, type PropsWithChildren, type ReactNode } from "react";

type ErrorBoundaryState = { failed: boolean };

export class AppErrorBoundary extends Component<PropsWithChildren, ErrorBoundaryState> {
  state: ErrorBoundaryState = { failed: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { failed: true };
  }

  componentDidCatch(error: unknown): void {
    if (import.meta.env?.DEV) {
      console.error(
        "unexpected_render_failure",
        error instanceof Error ? error.name : typeof error,
      );
    }
  }

  render(): ReactNode {
    if (!this.state.failed) return this.props.children;

    return createElement(
      "main",
      {
        className: "grid min-h-screen place-items-center bg-background px-5 py-12 text-foreground",
        role: "alert",
      },
      createElement(
        "section",
        { className: "w-full max-w-lg rounded-2xl border border-destructive/30 bg-card p-7 shadow-sm" },
        createElement("p", { className: "page-kicker" }, "Application recovery"),
        createElement("h1", { className: "page-title mt-2" }, "This page could not be displayed."),
        createElement(
          "p",
          { className: "mt-4 text-sm leading-6 text-muted-foreground" },
          "Reload the application to try again. If the problem continues, note what you were doing and contact YPGym support.",
        ),
        createElement(
          "button",
          {
            className: "mt-6 inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            onClick: () => window.location.reload(),
            type: "button",
          },
          "Reload application",
        ),
      ),
    );
  }
}
