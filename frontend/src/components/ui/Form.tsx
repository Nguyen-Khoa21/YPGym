import type { HTMLAttributes, InputHTMLAttributes, LabelHTMLAttributes, PropsWithChildren } from "react";

import { cn } from "@/lib/utils";

export function Field({ children, className }: PropsWithChildren<HTMLAttributes<HTMLDivElement>>) {
  return <div className={cn("space-y-2", className)}>{children}</div>;
}

export function Label({
  className,
  ...props
}: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn("text-sm font-semibold text-foreground", className)}
      {...props}
    />
  );
}

export function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-md border border-input bg-card px-3 text-sm outline-none transition placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:bg-muted",
        className,
      )}
      {...props}
    />
  );
}

export function FieldError({ message }: { message?: string }) {
  if (!message) {
    return null;
  }
  return <p className="text-sm font-medium text-destructive">{message}</p>;
}
