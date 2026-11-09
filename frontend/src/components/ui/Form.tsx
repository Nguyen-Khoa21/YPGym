import { createContext, useContext, useEffect, useId, useState, useSyncExternalStore } from "react";
import type {
  HTMLAttributes,
  InputHTMLAttributes,
  LabelHTMLAttributes,
  PropsWithChildren,
  TextareaHTMLAttributes,
} from "react";

import { cn } from "@/lib/utils";

/**
 * A Field gives its label, control and error message one shared id, so a label always points at its
 * control and an error is announced with it, without any change at the call site.
 * The FieldError reports "I have a message" to the Field, and the control reads that to set aria-invalid.
 */
type FieldContextValue = {
  controlId: string;
  errorId: string;
  subscribe: (listener: () => void) => () => void;
  hasError: () => boolean;
  setHasError: (value: boolean) => void;
};

const FieldContext = createContext<FieldContextValue | null>(null);
const noopSubscribe = () => () => {};
const never = () => false;

function createFieldContext(controlId: string): FieldContextValue {
  let error = false;
  const listeners = new Set<() => void>();
  return {
    controlId,
    errorId: `${controlId}-error`,
    subscribe(listener) {
      listeners.add(listener);
      return () => { listeners.delete(listener); };
    },
    hasError: () => error,
    setHasError(value) {
      if (error === value) return;
      error = value;
      listeners.forEach((listener) => listener());
    },
  };
}

export function Field({ children, className }: PropsWithChildren<HTMLAttributes<HTMLDivElement>>) {
  const id = useId();
  const [context] = useState(() => createFieldContext(id));
  return (
    <FieldContext.Provider value={context}>
      <div className={cn("space-y-2", className)}>{children}</div>
    </FieldContext.Provider>
  );
}

export function Label({
  className,
  htmlFor,
  ...props
}: LabelHTMLAttributes<HTMLLabelElement>) {
  const field = useContext(FieldContext);
  return (
    <label
      className={cn("text-sm font-semibold text-foreground", className)}
      htmlFor={htmlFor ?? field?.controlId}
      {...props}
    />
  );
}

function useControlA11y(id: string | undefined, describedBy: string | undefined) {
  const field = useContext(FieldContext);
  const invalid = useSyncExternalStore(field?.subscribe ?? noopSubscribe, field?.hasError ?? never, never);
  return {
    id: id ?? field?.controlId,
    "aria-invalid": invalid || undefined,
    "aria-describedby": [describedBy, invalid ? field?.errorId : undefined].filter(Boolean).join(" ") || undefined,
  };
}

const controlClasses =
  "w-full rounded-md border border-input bg-card px-3 text-sm outline-none transition placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:bg-muted aria-[invalid=true]:border-destructive aria-[invalid=true]:focus:ring-destructive/20";

export function Input({
  className,
  id,
  "aria-describedby": describedBy,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  const a11y = useControlA11y(id, describedBy);
  return <input className={cn("h-11", controlClasses, className)} {...a11y} {...props} />;
}

export function Textarea({
  className,
  id,
  "aria-describedby": describedBy,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const a11y = useControlA11y(id, describedBy);
  return <textarea className={cn("min-h-28 resize-y py-2.5", controlClasses, className)} {...a11y} {...props} />;
}

export function FieldError({ message }: { message?: string }) {
  const field = useContext(FieldContext);
  const setHasError = field?.setHasError;
  const present = Boolean(message);
  useEffect(() => {
    setHasError?.(present);
    return () => setHasError?.(false);
  }, [present, setHasError]);
  if (!message) {
    return null;
  }
  return <p id={field?.errorId} role="alert" className="text-sm font-medium text-destructive">{message}</p>;
}
