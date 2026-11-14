import { Download, ExternalLink, Printer, RefreshCw, X } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { downloadApiFile } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import type { InvoiceHistoryItem } from "@/types/api";

import { invoiceFileName, isPdfBlob, type ViewerState } from "../invoiceViewer";

type Props = { invoice: InvoiceHistoryItem; onClose: () => void };

/**
 * Modal PDF viewer. Uses a native <dialog> (focus trap, Esc, focus restore to the opener) and an
 * object URL created from an authenticated fetch, so no token ever appears in a URL.
 */
export function InvoiceViewerDialog({ invoice, onClose }: Props) {
  const { token } = useAuth();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const frameRef = useRef<HTMLIFrameElement>(null);
  const titleId = useId();
  const [state, setState] = useState<ViewerState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let objectUrl: string | null = null;
    downloadApiFile(invoice.download_url, token)
      .then((blob) => {
        if (controller.signal.aborted) return;
        if (!isPdfBlob(blob)) throw new Error("not a pdf");
        objectUrl = URL.createObjectURL(new Blob([blob], { type: "application/pdf" }));
        setState({ status: "ready", url: objectUrl });
      })
      .catch((caught) => {
        if (controller.signal.aborted) return;
        setState({ status: "error", message: toUiError(caught).message });
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [invoice.download_url, token, attempt]);

  const url = state.status === "ready" ? state.url : null;
  const download = useCallback(() => {
    if (!url) return;
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = invoiceFileName(invoice.invoice_number);
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
  }, [url, invoice.invoice_number]);

  const print = useCallback(() => {
    const frame = frameRef.current?.contentWindow;
    if (!frame) return;
    try {
      frame.focus();
      frame.print();
    } catch {
      // Some browsers block printing a embedded PDF; the new-tab viewer is the fallback.
      if (url) window.open(url, "_blank", "noopener");
    }
  }, [url]);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      className="m-auto h-[min(92dvh,56rem)] w-[min(96vw,60rem)] rounded-xl border border-border bg-card p-0 text-foreground shadow-2xl backdrop:bg-black/60"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="flex h-full flex-col">
        <header className="flex items-start justify-between gap-3 border-b border-border p-4">
          <div className="min-w-0">
            <h2
              id={titleId}
              className="truncate font-['Barlow_Condensed'] text-2xl font-bold uppercase"
            >
              Invoice {invoice.invoice_number}
            </h2>
            <p className="text-xs text-muted-foreground">{invoice.product_name}</p>
          </div>
          <button
            type="button"
            aria-label="Close invoice viewer"
            onClick={onClose}
            className="inline-flex size-11 shrink-0 items-center justify-center rounded-md hover:bg-muted"
          >
            <X className="size-5" aria-hidden />
          </button>
        </header>
        <div className="flex flex-wrap gap-2 border-b border-border p-3">
          <Button variant="primary" disabled={!url} onClick={download}>
            <Download className="size-4" aria-hidden />
            Download
          </Button>
          <Button variant="outline" disabled={!url} onClick={print}>
            <Printer className="size-4" aria-hidden />
            Print
          </Button>
          <Button
            variant="outline"
            disabled={!url}
            onClick={() => {
              if (url) window.open(url, "_blank", "noopener");
            }}
          >
            <ExternalLink className="size-4" aria-hidden />
            Open in new tab
          </Button>
          <Button variant="ghost" className="ml-auto" onClick={onClose}>
            Close
          </Button>
        </div>
        <div className="min-h-0 flex-1 bg-muted/40" aria-live="polite">
          {state.status === "loading" ? (
            <p className="p-6 text-sm text-muted-foreground" role="status">
              Loading invoice…
            </p>
          ) : null}
          {state.status === "error" ? (
            <div className="space-y-3 p-6" role="alert">
              <p className="text-sm font-semibold text-destructive">
                The invoice could not be loaded.
              </p>
              <p className="text-sm text-muted-foreground">{state.message}</p>
              <Button
                variant="outline"
                onClick={() => {
                  setState({ status: "loading" });
                  setAttempt((value) => value + 1);
                }}
              >
                <RefreshCw className="size-4" aria-hidden />
                Retry
              </Button>
            </div>
          ) : null}
          {state.status === "ready" ? (
            <iframe
              ref={frameRef}
              title={`Invoice ${invoice.invoice_number}`}
              src={state.url}
              className="size-full border-0 bg-white"
            />
          ) : null}
        </div>
        <p className="border-t border-border px-4 py-2 text-[11px] text-muted-foreground">
          If the preview is blank on your phone, use Open in new tab or Download.
        </p>
      </div>
    </dialog>
  );
}
