import { CalendarDays, Clock3, UserRound } from "lucide-react";

import { EmptyState } from "@/components/common/FeedbackState";
import { Panel } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { formatDateTime, formatMoney } from "@/lib/format";
import type { GymClass } from "@/types/operations";

type Props = {
  item: GymClass | undefined;
  onEdit: (item: GymClass) => void;
};

export function NextClassCard({ item, onEdit }: Props) {
  return (
    <Panel title="Next scheduled class" detail="Real backend schedule data only.">
      {item ? (
        <article className="p-5">
          <span className="inline-flex rounded-full bg-secondary px-3 py-1 text-[10px] font-black uppercase tracking-wider">
            {item.class_type}
          </span>
          <h3 className="mt-4 font-['Barlow_Condensed'] text-4xl font-bold uppercase">
            {item.title}
          </h3>
          <p className="mt-3 flex items-center gap-2 text-sm">
            <Clock3 className="size-4 text-primary" /> {formatDateTime(item.start_at)}
          </p>
          <p className="mt-2 flex items-center gap-2 text-sm">
            <UserRound className="size-4 text-primary" />{" "}
            {item.trainer_name ?? "Trainer unassigned"}
          </p>
          <p className="mt-2 flex items-center gap-2 text-sm">
            <CalendarDays className="size-4 text-primary" /> {item.location} / {item.capacity}{" "}
            places
          </p>
          <p className="mt-2 text-lg font-bold">
            {item.price_vnd ? formatMoney(item.price_vnd) : "Price not set"}
          </p>
          <Button className="mt-5" variant="outline" onClick={() => onEdit(item)}>
            Edit details
          </Button>
        </article>
      ) : (
        <EmptyState
          className="m-4"
          title="No upcoming class"
          message="Add a future class to populate this schedule card."
        />
      )}
    </Panel>
  );
}
