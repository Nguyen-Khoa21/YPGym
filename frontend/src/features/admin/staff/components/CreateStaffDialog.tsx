import type { UseFormReturn } from "react-hook-form";

import { Modal } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import type { StaffAccountForm } from "@/features/admin/staff/staffForm";
import type { GymLocation } from "@/types/operations";

type Props = {
  form: UseFormReturn<StaffAccountForm>;
  /** Only admins choose the gym; a manager's accounts go to their own gym on the server. */
  isAdmin: boolean;
  gyms: GymLocation[] | undefined;
  error: string | undefined;
  isPending: boolean;
  onSubmit: (values: StaffAccountForm) => void;
  onClose: () => void;
};

export function CreateStaffDialog({
  form,
  isAdmin,
  gyms,
  error,
  isPending,
  onSubmit,
  onClose,
}: Props) {
  return (
    <Modal
      title="Create workforce account"
      description="Managers can create staff and PT accounts only. Admin roles cannot be provisioned here."
      error={error}
      onClose={onClose}
    >
      <form className="ops-modal__body" onSubmit={form.handleSubmit(onSubmit)}>
        <div className="grid gap-4">
          <Field>
            <Label htmlFor="staff-name">Full name</Label>
            <Input id="staff-name" autoComplete="name" {...form.register("name")} />
            <FieldError message={form.formState.errors.name?.message} />
          </Field>
          <Field>
            <Label htmlFor="staff-login">Login name</Label>
            <Input
              id="staff-login"
              autoCapitalize="none"
              placeholder="alex.nguyen"
              {...form.register("login_name")}
            />
            <FieldError message={form.formState.errors.login_name?.message} />
          </Field>
          <Field>
            <Label htmlFor="staff-account-role">Role</Label>
            <select
              id="staff-account-role"
              className="h-11 w-full rounded-md border border-input bg-card px-3 text-sm"
              {...form.register("role")}
            >
              <option value="staff">Staff</option>
              <option value="pt">Personal trainer</option>
            </select>
          </Field>
          {isAdmin ? (
            <Field>
              <Label htmlFor="staff-gym">Gym location</Label>
              <select
                id="staff-gym"
                required
                className="h-11 w-full rounded-md border border-input bg-card px-3 text-sm"
                {...form.register("gym_id")}
              >
                <option value="">Select a gym</option>
                {gyms?.map((gym) => (
                  <option key={gym.id} value={gym.id}>
                    {gym.name}
                  </option>
                ))}
              </select>
            </Field>
          ) : null}
          <Field>
            <Label htmlFor="staff-phone">Phone (optional)</Label>
            <Input id="staff-phone" autoComplete="tel" {...form.register("phone")} />
            <FieldError message={form.formState.errors.phone?.message} />
          </Field>
        </div>
        <div className="ops-modal__actions">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isPending || (isAdmin && !gyms?.length)}>
            {isPending ? "Creating..." : "Create account"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
