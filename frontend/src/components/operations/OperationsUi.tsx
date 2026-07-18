import type { PropsWithChildren, ReactNode } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

export function OperationsHeader({ kicker, title, description, actions }: { kicker: string; title: string; description: string; actions?: ReactNode }) {
  return (
    <header className="ops-header">
      <div><p className="page-kicker">{kicker}</p><h1 className="page-title">{title}</h1><p className="page-description">{description}</p></div>
      {actions ? <div className="ops-header__actions">{actions}</div> : null}
    </header>
  );
}

export function MetricCard({ label, value, detail, tone = "paper" }: { label: string; value: string | number; detail?: string; tone?: "paper" | "forest" | "lime" | "coral" }) {
  return (
    <article className={cn("metric-card", `metric-card--${tone}`)}>
      <p>{label}</p><strong>{value}</strong>{detail ? <span>{detail}</span> : null}
    </article>
  );
}

export function StatusBadge({ value }: { value: string }) {
  const normalized = value.toLowerCase().replaceAll(" ", "_");
  return <span className={cn("status-badge", `status-badge--${normalized}`)}>{value.replaceAll("_", " ")}</span>;
}

export function Pagination({ page, pages, total, onPage }: { page: number; pages: number; total: number; onPage: (page: number) => void }) {
  return (
    <div className="ops-pagination">
      <p>{total} result{total === 1 ? "" : "s"}</p>
      <div><Button variant="outline" aria-label="Previous page" disabled={page <= 1} onClick={() => onPage(page - 1)}><ChevronLeft className="size-4" /></Button><span>Page {page} of {Math.max(pages, 1)}</span><Button variant="outline" aria-label="Next page" disabled={page >= pages} onClick={() => onPage(page + 1)}><ChevronRight className="size-4" /></Button></div>
    </div>
  );
}

export function Panel({ title, detail, actions, children, className }: PropsWithChildren<{ title: string; detail?: string; actions?: ReactNode; className?: string }>) {
  return (
    <section className={cn("ops-panel", className)}>
      <header className="ops-panel__header"><div><h2>{title}</h2>{detail ? <p>{detail}</p> : null}</div>{actions}</header>
      {children}
    </section>
  );
}

export function Modal({ title, description, onClose, children }: PropsWithChildren<{ title: string; description?: string; onClose: () => void }>) {
  return (
    <div className="ops-modal" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="ops-modal__panel" role="dialog" aria-modal="true" aria-labelledby="ops-modal-title">
        <header><div><h2 id="ops-modal-title">{title}</h2>{description ? <p>{description}</p> : null}</div><button type="button" aria-label="Close dialog" onClick={onClose}><X className="size-5" /></button></header>
        {children}
      </section>
    </div>
  );
}
