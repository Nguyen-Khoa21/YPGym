import type { UseFormReturn } from "react-hook-form";
import { useWatch } from "react-hook-form";

import { Modal } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label, Textarea } from "@/components/ui/Form";
import type { ClassForm } from "@/features/classes/classForm";
import type { GymClass, GymLocation, Trainer } from "@/types/operations";

type Props = {
  editing: GymClass | "new";
  form: UseFormReturn<ClassForm>;
  gyms: GymLocation[] | undefined;
  trainers: Trainer[] | undefined;
  error?: string;
  isPending: boolean;
  onSubmit: (values: ClassForm) => void;
  onClose: () => void;
};

export function ClassFormDialog({
  editing,
  form,
  gyms,
  trainers,
  error,
  isPending,
  onSubmit,
  onClose,
}: Props) {
  const descriptionLength = (useWatch({ control: form.control, name: "description" }) ?? "").length;
  const errors = form.formState.errors;
  return (
    <Modal
      error={error}
      title={editing === "new" ? "Schedule a class" : `Edit ${editing.title}`}
      description="Timezone, future time, capacity, trainer availability, and resource overlap are validated by the server."
      onClose={onClose}
    >
      <form className="ops-modal__body" onSubmit={form.handleSubmit(onSubmit)}>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field>
            <Label>Title</Label>
            <Input {...form.register("title")} />
            <FieldError message={errors.title?.message} />
          </Field>
          <Field>
            <Label>Class type</Label>
            <Input {...form.register("class_type")} />
            <FieldError message={errors.class_type?.message} />
          </Field>
          <Field>
            <Label>Gym location</Label>
            <select
              className="h-11 rounded-md border border-input px-3"
              {...form.register("gym_id")}
            >
              <option value="">Select a gym</option>
              {gyms?.map((gym) => (
                <option value={gym.id} key={gym.id}>
                  {gym.name} · {gym.district}
                </option>
              ))}
            </select>
            <FieldError message={errors.gym_id?.message} />
          </Field>
          <Field>
            <Label>Room / area</Label>
            <Input {...form.register("location")} />
            <FieldError message={errors.location?.message} />
          </Field>
          <Field>
            <Label>Start</Label>
            <Input type="datetime-local" {...form.register("start_at")} />
            <FieldError message={errors.start_at?.message} />
          </Field>
          <Field>
            <Label>End</Label>
            <Input type="datetime-local" {...form.register("end_at")} />
            <FieldError message={errors.end_at?.message} />
          </Field>
          <Field>
            <Label>Capacity</Label>
            <Input
              type="number"
              min="1"
              max="500"
              {...form.register("capacity", { valueAsNumber: true })}
            />
            <FieldError message={errors.capacity?.message} />
          </Field>
          <Field>
            <Label>Price (VND)</Label>
            <Input
              type="number"
              min="1"
              step="1000"
              {...form.register("price_vnd", { valueAsNumber: true })}
            />
            <FieldError message={errors.price_vnd?.message} />
          </Field>
          <Field className="sm:col-span-2">
            <Label>Trainer</Label>
            <select
              className="h-11 rounded-md border border-input px-3"
              {...form.register("trainer_id")}
            >
              <option value="">Unassigned</option>
              {trainers?.map((trainer) => (
                <option value={trainer.id} key={trainer.id}>
                  {trainer.display_name}
                  {trainer.specialty ? ` - ${trainer.specialty}` : ""}
                </option>
              ))}
            </select>
          </Field>
          <Field className="sm:col-span-2">
            <Label htmlFor="class-description">Description</Label>
            <Textarea
              id="class-description"
              className="min-h-32 w-full resize-y"
              {...form.register("description")}
            />
            <div className="flex items-start justify-between gap-3">
              <FieldError message={errors.description?.message} />
              <span className="ml-auto text-xs text-muted-foreground" aria-live="polite">
                {descriptionLength}/3000
              </span>
            </div>
          </Field>
        </div>
        <div className="ops-modal__actions">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending ? "Saving..." : editing === "new" ? "Schedule class" : "Save changes"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
