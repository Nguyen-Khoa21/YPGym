/** The server marks a verified payOS payment `paid` and never moves it on; `succeeded` is the legacy equivalent. */
export function isPaidStatus(status: string | undefined): boolean {
  return status === "paid" || status === "succeeded";
}

type PaymentTone = "wait" | "ok" | "bad";

/** Single source for how each payment status reads and whether it ends polling. */
const PAYMENT_STATUS: Record<string, { label: string; tone: PaymentTone; final: boolean }> = {
  paid: { label: "Paid. Membership is active.", tone: "ok", final: true },
  succeeded: { label: "Paid. Membership is active.", tone: "ok", final: true },
  paid_review: { label: "Paid, but needs manager review before activation.", tone: "bad", final: true },
  failed: { label: "Payment failed.", tone: "bad", final: true },
  cancelled: { label: "Payment was cancelled.", tone: "bad", final: true },
  expired: { label: "The QR code expired.", tone: "bad", final: true },
};
const WAITING = { label: "Waiting for the member to pay.", tone: "wait" as PaymentTone, final: false };

/** A final status ends polling. */
export function isFinalPaymentStatus(status: string): boolean {
  return (PAYMENT_STATUS[status] ?? WAITING).final;
}

export function paymentStatusLabel(status: string): { label: string; tone: PaymentTone } {
  return PAYMENT_STATUS[status] ?? WAITING;
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
