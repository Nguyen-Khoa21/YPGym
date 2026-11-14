// Carries "renew at my gym" or "change location" from the expired-membership panel to the checkout page.
// The intent only preselects (or deliberately does not preselect) a gym. The home gym itself changes
// only after a verified payment, exactly as before.
export type RenewalIntent =
  { mode: "renew"; gymId: string } | { mode: "change" } | { mode: "default" };

export function isExpiredStatus(status: string | null | undefined) {
  return status === "expired";
}

export function renewalSearch(intent: RenewalIntent) {
  if (intent.mode === "renew") return `?gym=${encodeURIComponent(intent.gymId)}`;
  if (intent.mode === "change") return "?change=1";
  return "";
}

export function readRenewalIntent(params: URLSearchParams): RenewalIntent {
  if (params.get("change") === "1") return { mode: "change" };
  const gymId = params.get("gym");
  return gymId ? { mode: "renew", gymId } : { mode: "default" };
}

/** The gym to preselect at checkout, in priority order. An empty string means nothing is preselected. */
export function checkoutGymId(args: {
  chosen: string;
  intent: RenewalIntent;
  homeGymId?: string | null;
  hasMembership: boolean;
  recommendedGymId?: string | null;
}) {
  if (args.chosen) return args.chosen;
  if (args.intent.mode === "change") return "";
  if (args.intent.mode === "renew") return args.intent.gymId;
  if (args.homeGymId) return args.homeGymId;
  return args.hasMembership ? "" : (args.recommendedGymId ?? "");
}
