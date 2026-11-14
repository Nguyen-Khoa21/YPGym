import { Button } from "@/components/ui/Button";
import { Field, Input, Label } from "@/components/ui/Form";
import type { StaffFilters } from "@/features/admin/staff/staffFilters";

type Props = {
  filters: StaffFilters;
  onChange: (patch: Partial<StaffFilters>) => void;
  onClear: () => void;
};

const SELECT_CLASS = "h-11 w-full rounded-md border border-input bg-card px-3 text-sm";

export function StaffFilterBar({ filters, onChange, onClear }: Props) {
  return (
    <>
      <div className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Field className="lg:col-span-2">
          <Label htmlFor="staff-search">Name or login</Label>
          <Input
            id="staff-search"
            value={filters.search}
            onChange={(event) => onChange({ search: event.target.value })}
          />
        </Field>
        <Field>
          <Label htmlFor="staff-role">Role</Label>
          <select
            id="staff-role"
            className={SELECT_CLASS}
            value={filters.role}
            onChange={(event) => onChange({ role: event.target.value })}
          >
            <option value="">All roles</option>
            <option value="staff">Staff</option>
            <option value="pt">PT</option>
          </select>
        </Field>
        <Field>
          <Label htmlFor="shift-status">Shift status</Label>
          <select
            id="shift-status"
            className={SELECT_CLASS}
            value={filters.status}
            onChange={(event) => onChange({ status: event.target.value })}
          >
            <option value="">All shifts</option>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
          </select>
        </Field>
        <div className="flex items-end">
          <Button className="w-full" variant="outline" onClick={onClear}>
            Clear filters
          </Button>
        </div>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <Field>
          <Label htmlFor="shift-from">Shift date from</Label>
          <Input
            id="shift-from"
            type="date"
            value={filters.dateFrom}
            onChange={(event) => onChange({ dateFrom: event.target.value })}
          />
        </Field>
        <Field>
          <Label htmlFor="shift-to">Shift date to</Label>
          <Input
            id="shift-to"
            type="date"
            value={filters.dateTo}
            min={filters.dateFrom || undefined}
            onChange={(event) => onChange({ dateTo: event.target.value })}
          />
        </Field>
      </div>
    </>
  );
}
