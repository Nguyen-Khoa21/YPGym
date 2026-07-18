import { Slot } from "@radix-ui/react-slot";
import type { ButtonHTMLAttributes, AnchorHTMLAttributes, PropsWithChildren } from "react";

import { cn } from "@/lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "outline" | "danger";
};

const buttonClasses = {
  primary:
    "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 disabled:bg-primary/60",
  secondary:
    "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/90 disabled:bg-secondary/60",
  ghost: "bg-transparent text-foreground hover:bg-muted disabled:text-muted-foreground",
  outline:
    "border border-border bg-card text-foreground shadow-sm hover:bg-muted disabled:text-muted-foreground",
  danger:
    "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90 disabled:bg-destructive/60",
};

export function Button({
  className,
  variant = "primary",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition-[transform,background-color,color,border-color] duration-150 ease-out active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:active:scale-100",
        buttonClasses[variant],
        className,
      )}
      {...props}
    />
  );
}

type ButtonLinkProps = PropsWithChildren<
  AnchorHTMLAttributes<HTMLAnchorElement> & {
    asChild?: boolean;
    variant?: keyof typeof buttonClasses;
  }
>;

export function ButtonLink({
  asChild,
  className,
  variant = "primary",
  ...props
}: ButtonLinkProps) {
  const Component = asChild ? Slot : "a";
  return (
    <Component
      className={cn(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition-[transform,background-color,color,border-color] duration-150 ease-out active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        buttonClasses[variant],
        className,
      )}
      {...props}
    />
  );
}
