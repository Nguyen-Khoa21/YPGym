import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { BadgeCheck, Banknote, Copy, QrCode } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Modal } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import type { OperationsScope } from "@/features/operations/useOperationsScope";
import { apiRequest } from "@/lib/apiClient";
import { applyApiFieldErrors, toUiError } from "@/lib/apiErrors";
import { formatMoney } from "@/lib/format";
import type { MembershipPlan, PayOSCreateResponse, PurchaseResponse } from "@/types/api";
import type { InPersonMemberRegistered, StaffPaymentStatus } from "@/types/operations";

import { isFinalPaymentStatus, newPaymentKey, paymentStatusLabel, qrValue } from "../inPersonRegistration";

const schema = z.object({
  name: z.string().trim().min(2, "Enter the member's full name."),
  email: z.string().trim().email("Enter a valid email address."),
  phone: z.string().trim().min(7, "Phone number is too short."),
});
type DetailsForm = z.infer<typeof schema>;
type Step = "details" | "plan" | "pay" | "done";
type Outcome = { kind: "cash"; result: PurchaseResponse } | { kind: "qr"; checkout: PayOSCreateResponse } | null;

/**
 * Register a walk-in member, choose a plan, then take payment by cash or payOS QR.
 * The server derives the gym and the price; this dialog only displays them.
 */
export function InPersonRegistrationDialog({ scope, onClose }: { scope: OperationsScope; onClose: () => void }) {
  const { token } = useAuth();
  const [stepState, setStep] = useState<Step>("details");
  const [ownerGymId, setOwnerGymId] = useState(scope.gymId || scope.gyms[0]?.id || "");
  const [registered, setRegistered] = useState<InPersonMemberRegistered | null>(null);
  const [plan, setPlan] = useState<MembershipPlan | null>(null);
  const [confirmCash, setConfirmCash] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);
  const [formError, setFormError] = useState<string | null>(null);
  // One key per plan choice: retries are idempotent, and a different plan gets a new key.
  const [attempt, setAttempt] = useState(0);
  // eslint-disable-next-line react-hooks/exhaustive-deps -- attempt intentionally regenerates the keys after a failed QR
  const keys = useMemo(() => ({ qr: newPaymentKey("qr"), cash: newPaymentKey("cash") }), [plan?.id, attempt]);
  const gymName = scope.isOwner ? scope.gyms.find((gym) => gym.id === ownerGymId)?.name : scope.gymName;
  const gymBody = scope.isOwner ? { gym_id: ownerGymId } : {};

  const form = useForm<DetailsForm>({ resolver: zodResolver(schema), defaultValues: { name: "", email: "", phone: "" } });
  const plans = useQuery({
    queryKey: ["membership-plans"],
    queryFn: ({ signal }) => apiRequest<MembershipPlan[]>("/membership-plans", { signal }),
    enabled: stepState === "plan",
  });

  const register = useMutation({
    mutationFn: (values: DetailsForm) => apiRequest<InPersonMemberRegistered>("/staff/members", { method: "POST", token, body: { ...values, ...gymBody } }),
    onSuccess: (data) => { setRegistered(data); setStep("plan"); setFormError(null); },
  });
  const cash = useMutation({
    mutationFn: () => apiRequest<PurchaseResponse>(`/staff/members/${registered?.member.id}/membership-cash`, { method: "POST", token, body: { plan_id: plan?.id, idempotency_key: keys.cash, ...gymBody } }),
    onSuccess: (result) => { setOutcome({ kind: "cash", result }); setStep("done"); },
  });
  const qr = useMutation({
    mutationFn: () => apiRequest<PayOSCreateResponse>(`/staff/members/${registered?.member.id}/membership-checkout`, { method: "POST", token, body: { plan_id: plan?.id, idempotency_key: keys.qr, ...gymBody } }),
    onSuccess: (checkout) => setOutcome({ kind: "qr", checkout }),
  });

  const qrCheckout = outcome?.kind === "qr" ? outcome.checkout : null;
  const status = useQuery({
    queryKey: ["staff", "payment-status", qrCheckout?.transaction_id],
    queryFn: ({ signal }) => apiRequest<StaffPaymentStatus>(`/staff/payments/${qrCheckout?.transaction_id}`, { token, signal }),
    enabled: Boolean(qrCheckout) && stepState === "pay",
    refetchInterval: (query) => (query.state.data && isFinalPaymentStatus(query.state.data.status) ? false : 3000),
  });
  const paid = status.data?.status === "succeeded";
  // A verified payment moves the dialog to the done screen without an effect.
  const step: Step = paid ? "done" : stepState;

  async function submitDetails(values: DetailsForm) {
    setFormError(null);
    try {
      await register.mutateAsync(values);
    } catch (caught) {
      if (!applyApiFieldErrors(caught, form.setError, ["name", "email", "phone"])) setFormError(toUiError(caught).message);
    }
  }

  const stepTitle = { details: "Register new member", plan: "Choose a membership", pay: "Take payment", done: "Member is ready" }[step];
  const activeError = cash.isError ? toUiError(cash.error).message : qr.isError ? toUiError(qr.error).message : formError ?? undefined;
  const stepNumber = { details: 1, plan: 2, pay: 3, done: 4 }[step];

  return <Modal title={stepTitle} description={`Step ${stepNumber} of 4${gymName ? ` · ${gymName}` : ""}`} error={activeError} onClose={onClose}>
    <div className="ops-modal__body" aria-live="polite">
      {registered && step !== "done" ? <TemporaryPassword password={registered.temporary_password} /> : null}

      {step === "details" ? <form className="grid gap-4" onSubmit={form.handleSubmit(submitDetails)} noValidate>
        {scope.isOwner ? <Field><Label>Gym</Label><select value={ownerGymId} onChange={(event) => setOwnerGymId(event.target.value)} aria-label="Gym for the new member">{scope.gyms.map((gym) => <option key={gym.id} value={gym.id}>{gym.name}</option>)}</select></Field> : <p className="text-sm text-muted-foreground">Gym: <strong>{gymName ?? "Loading your gym"}</strong>. The new member is linked to this gym.</p>}
        <Field><Label>Full name</Label><Input autoComplete="off" {...form.register("name")} /><FieldError message={form.formState.errors.name?.message} /></Field>
        <Field><Label>Email</Label><Input type="email" autoComplete="off" {...form.register("email")} /><FieldError message={form.formState.errors.email?.message} /></Field>
        <Field><Label>Phone</Label><Input type="tel" autoComplete="off" {...form.register("phone")} /><FieldError message={form.formState.errors.phone?.message} /></Field>
        <p className="text-xs text-muted-foreground">No email verification is needed. The member receives a one-time temporary password and must change it on first sign-in. If the email already exists, ask the member to renew online or ask a manager.</p>
        <div className="ops-modal__actions"><Button variant="outline" onClick={onClose}>Cancel</Button><Button type="submit" disabled={register.isPending || (scope.isOwner && !ownerGymId)}>{register.isPending ? "Registering..." : "Register member"}</Button></div>
      </form> : null}

      {step === "plan" ? <div className="grid gap-3">
        {plans.isLoading ? <p role="status" className="text-sm text-muted-foreground">Loading plans…</p> : null}
        {plans.isError ? <div role="alert"><p className="text-sm text-destructive">{toUiError(plans.error).message}</p><Button variant="outline" onClick={() => void plans.refetch()}>Retry</Button></div> : null}
        <fieldset className="grid gap-2"><legend className="mb-1 text-sm font-semibold">Plan for {registered?.member.name}</legend>
          {plans.data?.filter((item) => item.is_active).map((item) => <label key={item.id} className={`flex cursor-pointer items-center justify-between gap-3 rounded-lg border p-3 ${plan?.id === item.id ? "border-primary bg-primary/5" : "border-border"}`}><span className="flex items-center gap-3"><input type="radio" name="plan" checked={plan?.id === item.id} onChange={() => setPlan(item)} /><span><strong className="block text-sm">{item.name}</strong><span className="text-xs text-muted-foreground">{item.duration_days} days</span></span></span><strong>{formatMoney(item.final_price)}</strong></label>)}
        </fieldset>
        <div className="ops-modal__actions"><Button variant="outline" onClick={onClose}>Decide later</Button><Button disabled={!plan} onClick={() => setStep("pay")}>Continue to payment</Button></div>
      </div> : null}

      {step === "pay" && plan ? <div className="grid gap-4">
        <p className="rounded-lg bg-muted p-3 text-sm"><strong>{plan.name}</strong> · {gymName} · <strong>{formatMoney(plan.final_price)}</strong></p>
        {!qrCheckout && !confirmCash ? <div className="grid gap-3 sm:grid-cols-2">
          <Button variant="outline" className="h-auto min-h-20 flex-col" onClick={() => setConfirmCash(true)}><Banknote className="size-5" aria-hidden />Pay with cash</Button>
          <Button variant="outline" className="h-auto min-h-20 flex-col" disabled={qr.isPending} onClick={() => qr.mutate()}><QrCode className="size-5" aria-hidden />{qr.isPending ? "Creating QR…" : "Pay by QR"}</Button>
        </div> : null}
        {confirmCash ? <div role="group" aria-label="Confirm cash payment" className="grid gap-3 rounded-lg border border-border p-4">
          <p className="text-sm font-semibold">Confirm you received {formatMoney(plan.final_price)} in cash.</p>
          <p className="text-xs text-muted-foreground">This activates the membership and issues an invoice. It cannot be undone from this screen.</p>
          <div className="ops-modal__actions"><Button variant="outline" disabled={cash.isPending} onClick={() => setConfirmCash(false)}>Back</Button><Button disabled={cash.isPending} onClick={() => cash.mutate()}>{cash.isPending ? "Recording…" : "Cash received"}</Button></div>
        </div> : null}
        {qrCheckout ? <div className="grid justify-items-center gap-3 text-center">
          <div className="rounded-xl bg-white p-4"><QRCodeSVG value={qrValue(qrCheckout)} size={240} marginSize={2} title={`Payment QR for ${plan.name}`} /></div>
          <p className="text-lg font-bold">{formatMoney(qrCheckout.amount_vnd)}</p>
          <p className="text-xs text-muted-foreground">{plan.name} · {qrCheckout.gym_name}</p>
          {(() => { const info = paymentStatusLabel(status.data?.status ?? "pending"); return <p role="status" className={`rounded-full px-3 py-1 text-xs font-bold ${info.tone === "ok" ? "bg-secondary/30" : info.tone === "bad" ? "bg-destructive/10 text-destructive" : "bg-muted"}`}>{info.tone === "ok" ? "✓ " : info.tone === "bad" ? "! " : "… "}{info.label}</p>; })()}
          {status.isError ? <p role="alert" className="text-xs text-destructive">{toUiError(status.error).message}</p> : null}
          {status.data && isFinalPaymentStatus(status.data.status) && !paid ? <Button variant="outline" onClick={() => { setOutcome(null); qr.reset(); setAttempt((value) => value + 1); }}>Back to payment options</Button> : null}
        </div> : null}
      </div> : null}

      {step === "done" && registered ? <div className="grid gap-4">
        <p className="flex items-center gap-2 text-sm font-semibold"><BadgeCheck className="size-5 text-primary" aria-hidden />{registered.member.name} is registered{outcome ? ` and ${outcome.kind === "cash" ? "paid in cash" : "paid by QR"}` : " and has paid"} at {registered.member.gym_name}.</p>
        <TemporaryPassword password={registered.temporary_password} emphasised />
        <p className="text-sm">Member signs in with <strong>{registered.member.email}</strong> and the temporary password, then sets a new password.</p>
        <div className="ops-modal__actions"><Button onClick={onClose}>Done</Button></div>
      </div> : null}
    </div>
  </Modal>;
}

function TemporaryPassword({ password, emphasised = false }: { password: string; emphasised?: boolean }) {
  const [shown, setShown] = useState(emphasised);
  async function copy() {
    try {
      await navigator.clipboard.writeText(password);
      toast.success("Temporary password copied");
    } catch {
      toast.error("Copy failed. Select the password and copy it manually.");
    }
  }
  return <div className="rounded-lg border border-secondary/60 bg-secondary/10 p-3" role="group" aria-label="Temporary password">
    <p className="text-xs font-bold uppercase tracking-wide">Temporary password (shown once)</p>
    <div className="mt-2 flex flex-wrap items-center gap-2">
      <code className="rounded bg-card px-2 py-1 font-mono text-sm select-all">{shown ? password : "••••••••••••••••••••"}</code>
      <Button variant="outline" className="min-h-9 px-3" onClick={() => setShown((value) => !value)}>{shown ? "Hide" : "Show"}</Button>
      <Button variant="outline" className="min-h-9 px-3" onClick={() => void copy()}><Copy className="size-4" aria-hidden />Copy</Button>
    </div>
  </div>;
}
