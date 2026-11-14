import { Clipboard, UsersRound } from "lucide-react";
import { toast } from "sonner";

import { Modal } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import type { StaffAccountCreated } from "@/types/operations";

type Props = {
  created: StaffAccountCreated;
  onClose: () => void;
};

/** Reveals the one-time temporary password right after an account is created. */
export function TemporaryCredentialsDialog({ created, onClose }: Props) {
  return (
    <Modal title="Copy temporary credentials" description={created.message} onClose={onClose}>
      <div className="ops-modal__body">
        <div className="rounded-xl border border-border bg-muted/40 p-4">
          <p className="text-xs font-black uppercase tracking-wider text-muted-foreground">Login</p>
          <code className="mt-1 block break-all text-sm font-bold">{created.account.email}</code>
          <p className="mt-4 text-xs font-black uppercase tracking-wider text-muted-foreground">
            Temporary password
          </p>
          <code className="mt-1 block break-all text-sm font-bold">
            {created.temporary_password}
          </code>
        </div>
        <p className="text-sm leading-6 text-muted-foreground">
          Share these credentials privately. The user must replace the password at first login. This
          internal login domain is not presented as a deliverable email inbox.
        </p>
        <div className="ops-modal__actions">
          <Button
            variant="outline"
            onClick={() =>
              void navigator.clipboard
                .writeText(`${created.account.email}\n${created.temporary_password}`)
                .then(() => toast.success("Credentials copied"))
            }
          >
            <Clipboard className="size-4" /> Copy
          </Button>
          <Button onClick={onClose}>
            <UsersRound className="size-4" /> Done
          </Button>
        </div>
      </div>
    </Modal>
  );
}
