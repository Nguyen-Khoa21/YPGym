import { useState } from "react";

import { Modal } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import type { GymClass } from "@/types/operations";

type Props = {
  item: GymClass;
  error?: string;
  isPending: boolean;
  onConfirm: (reason: string) => void;
  onClose: () => void;
};

/** Mounted only while a class is being cancelled, so the reason starts empty every time. */
export function CancelClassDialog({ item, error, isPending, onConfirm, onClose }: Props) {
  const [reason, setReason] = useState("");
  return (
    <Modal
      error={error}
      title={`Cancel ${item.title}?`}
      description="Cancellation is an audited status transition; the class is never hard-deleted."
      onClose={onClose}
    >
      <div className="ops-modal__body">
        <label>
          Mandatory cancellation reason
          <textarea value={reason} onChange={(event) => setReason(event.target.value)} />
        </label>
        <div className="ops-modal__actions">
          <Button variant="outline" onClick={onClose}>
            Keep class
          </Button>
          <Button
            variant="danger"
            disabled={reason.trim().length < 10 || isPending}
            onClick={() => onConfirm(reason.trim())}
          >
            {isPending ? "Cancelling..." : "Confirm cancellation"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
