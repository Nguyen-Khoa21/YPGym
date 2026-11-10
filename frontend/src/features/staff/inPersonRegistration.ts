export type StaffPaymentState = "pending" | "paid" | "succeeded" | "failed" | "cancelled" | "expired" | "paid_review";

/** The server marks a verified payOS payment `paid` and never moves it on; `succeeded` is the legacy equivalent. */
export function isPaidStatus(status: string | undefined): boolean {
  return status === "paid" || status === "succeeded";
}

/** A final status ends polling. */
export function isFinalPaymentStatus(status: string): boolean {
  return ["paid", "succeeded", "failed", "cancelled", "expired", "paid_review"].includes(status);
}

export function paymentStatusLabel(status: string): { label: string; tone: "wait" | "ok" | "bad" } {
  switch (status) {
    case "paid":
    case "succeeded": return { label: "Paid. Membership is active.", tone: "ok" };
    case "paid_review": return { label: "Paid, but needs manager review before activation.", tone: "bad" };
    case "failed": return { label: "Payment failed.", tone: "bad" };
    case "cancelled": return { label: "Payment was cancelled.", tone: "bad" };
    case "expired": return { label: "The QR code expired.", tone: "bad" };
    default: return { label: "Waiting for the member to pay.", tone: "wait" };
  }
}

/** payOS returns a bank QR payload; fall back to encoding the checkout link when it is absent. */
export function qrValue(checkout: { qr_code?: string | null; checkout_url: string }): string {
  return checkout.qr_code?.trim() || checkout.checkout_url;
}

/** One key per attempt: a repeated click or retry with the same key never creates a second payment. */
export function newPaymentKey(prefix: "qr" | "cash"): string {
  const random = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}-${random}`;
}
