import type { ColumnDef } from "@tanstack/react-table";
import { Pencil } from "lucide-react";

import { StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { formatDateTime, formatMoney } from "@/lib/format";
import type { GymClass } from "@/types/operations";

type Options = {
  gymNames: Map<string, string>;
  onEdit: (item: GymClass) => void;
  onCancel: (item: GymClass) => void;
};

export function classColumns({ gymNames, onEdit, onCancel }: Options): ColumnDef<GymClass>[] {
  return [
    {
      header: "Class",
      cell: ({ row }) => (
        <div>
          <strong>{row.original.title}</strong>
          <p className="mt-1 text-[11px] text-muted-foreground">
            {row.original.class_type} / {gymNames.get(row.original.gym_id) ?? "Gym"} /{" "}
            {row.original.location}
          </p>
        </div>
      ),
    },
    {
      header: "Schedule",
      cell: ({ row }) => (
        <div>
          <strong>{formatDateTime(row.original.start_at)}</strong>
          <p className="mt-1 text-[11px] text-muted-foreground">
            to {formatDateTime(row.original.end_at)}
          </p>
        </div>
      ),
    },
    { header: "Trainer", cell: ({ row }) => row.original.trainer_name ?? "Unassigned" },
    { header: "Capacity", accessorKey: "capacity" },
    {
      header: "Price",
      cell: ({ row }) => (row.original.price_vnd ? formatMoney(row.original.price_vnd) : "Not set"),
    },
    { header: "Status", cell: ({ row }) => <StatusBadge value={row.original.status} /> },
    {
      header: "Actions",
      cell: ({ row }) =>
        row.original.status === "scheduled" ? (
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => onEdit(row.original)}>
              <Pencil className="size-4" /> Edit
            </Button>
            <Button variant="danger" onClick={() => onCancel(row.original)}>
              Cancel
            </Button>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">No actions</span>
        ),
    },
  ];
}
