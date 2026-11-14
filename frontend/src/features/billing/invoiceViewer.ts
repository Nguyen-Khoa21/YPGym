/** Safe, predictable file name for a downloaded invoice (never trusts server-provided names). */
export function invoiceFileName(invoiceNumber: string): string {
  const safe = invoiceNumber
    .replace(/[^A-Za-z0-9._-]+/g, "-")
    .replace(/^[-.]+|[-.]+$/g, "")
    .slice(0, 80);
  return `${safe || "invoice"}.pdf`;
}

/** True only for a real PDF payload; a JSON/HTML error body must never reach the viewer. */
export function isPdfBlob(blob: Blob): boolean {
  return blob.size > 0 && (blob.type === "application/pdf" || blob.type === "");
}

export type ViewerState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; url: string }
  | { status: "error"; message: string };
