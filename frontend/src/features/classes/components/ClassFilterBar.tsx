import type { Dispatch, SetStateAction } from "react";
import { Search } from "lucide-react";

import { Button } from "@/components/ui/Button";
import type { ClassFilters } from "@/features/classes/classFilters";
import type { GymLocation, Trainer } from "@/types/operations";

type Props = {
  filters: ClassFilters;
  setFilters: Dispatch<SetStateAction<ClassFilters>>;
  /** The gym the list is currently showing; the gym select falls back to it. */
  gymId: string;
  gyms: GymLocation[] | undefined;
  trainers: Trainer[] | undefined;
  onApply: () => void;
};

export function ClassFilterBar({ filters, setFilters, gymId, gyms, trainers, onApply }: Props) {
  const setFilter = (key: keyof ClassFilters) => (event: { target: { value: string } }) =>
    setFilters((current) => ({ ...current, [key]: event.target.value }));
  return (
    <form
      className="ops-toolbar"
      onSubmit={(event) => {
        event.preventDefault();
        onApply();
      }}
    >
      <Search className="size-4 text-muted-foreground" />
      <input
        aria-label="Search classes"
        placeholder="Title or class type"
        value={filters.search}
        onChange={setFilter("search")}
      />
      <select
        aria-label="Filter gym location"
        value={filters.gymId || gymId}
        onChange={setFilter("gymId")}
      >
        <option value="">Select gym</option>
        {gyms?.map((gym) => (
          <option value={gym.id} key={gym.id}>
            {gym.name}
          </option>
        ))}
      </select>
      <select
        aria-label="Filter class status"
        value={filters.status}
        onChange={setFilter("status")}
      >
        <option value="">All statuses</option>
        <option value="scheduled">Scheduled</option>
        <option value="cancelled">Cancelled</option>
        <option value="completed">Completed</option>
      </select>
      <select
        aria-label="Filter trainer"
        value={filters.trainerId}
        onChange={setFilter("trainerId")}
      >
        <option value="">All trainers</option>
        {trainers?.map((trainer) => (
          <option value={trainer.id} key={trainer.id}>
            {trainer.display_name}
          </option>
        ))}
      </select>
      <input
        aria-label="Classes from"
        type="datetime-local"
        value={filters.dateFrom}
        onChange={setFilter("dateFrom")}
      />
      <input
        aria-label="Classes to"
        type="datetime-local"
        value={filters.dateTo}
        onChange={setFilter("dateTo")}
      />
      <Button type="submit" variant="secondary">
        Apply
      </Button>
    </form>
  );
}
