import type { ReactNode } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { Button } from "@/components/ui/Button";
import { toUiError } from "@/lib/apiErrors";

/** The slice of a TanStack query result that QueryState reads. */
type QueryLike<T> = {
  data: T | undefined;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => unknown;
};

type Props<T> = {
  query: QueryLike<T>;
  /** Spacing applied to each feedback panel, e.g. "m-4" or "mt-6". */
  className?: string;
  loading: { title: string; message?: string };
  /** Shows a Retry button on error: `true` for "Retry", or a custom label. Omit for none. */
  retry?: boolean | string;
  /** Shown instead of `children` when `isEmpty(data)` is true. Omit when "no rows" is not a state. */
  empty?: { title: string; message?: string };
  isEmpty?: (data: T) => boolean;
  /** Rendered whenever data is available and not empty, even if a later refetch failed. */
  children: (data: T) => ReactNode;
};

/**
 * Renders the loading, error, empty and loaded states of one query in the same order every page
 * used to hand-write. An error and stale data can show together: a failed refetch keeps the
 * previous data on screen, and the empty state appears only once data has loaded.
 */
export function QueryState<T>({
  query,
  className,
  loading,
  retry,
  empty,
  isEmpty,
  children,
}: Props<T>) {
  const { data } = query;
  const error = query.isError ? toUiError(query.error) : null;
  const showEmpty = data !== undefined && Boolean(empty) && Boolean(isEmpty?.(data));
  return (
    <>
      {query.isLoading ? (
        <LoadingState className={className} title={loading.title} message={loading.message} />
      ) : null}
      {error ? (
        <ErrorState
          className={className}
          title={error.title}
          message={error.message}
          action={
            retry ? (
              <Button variant="outline" onClick={() => void query.refetch()}>
                {typeof retry === "string" ? retry : "Retry"}
              </Button>
            ) : undefined
          }
        />
      ) : null}
      {showEmpty && empty ? (
        <EmptyState className={className} title={empty.title} message={empty.message} />
      ) : null}
      {data !== undefined && !showEmpty ? children(data) : null}
    </>
  );
}
