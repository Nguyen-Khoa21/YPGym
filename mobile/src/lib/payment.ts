export const terminalPaymentStatuses = new Set(['paid', 'paid_review', 'failed', 'cancelled', 'expired']);

export function shouldPollPayment(status: string | undefined, timedOut = false) {
  return !timedOut && (!status || !terminalPaymentStatuses.has(status));
}
