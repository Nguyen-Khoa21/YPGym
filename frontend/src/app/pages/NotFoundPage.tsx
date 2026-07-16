import { ArrowLeft, MapPinned } from "lucide-react";
import { Link } from "react-router-dom";

import { AppFrame } from "@/components/layout/AppFrame";

export function NotFoundPage() {
  return <AppFrame>
    <main id="main-content" className="mx-auto grid min-h-[calc(100vh-4.8rem)] max-w-4xl place-items-center px-5 py-10"><section className="surface-card max-w-xl p-8 text-center sm:p-12"><span className="mx-auto grid size-14 place-items-center rounded-2xl bg-muted text-primary"><MapPinned className="size-6" aria-hidden /></span><p className="page-kicker mt-6">404 route not found</p><h1 className="mt-2 font-['Barlow_Condensed'] text-5xl font-bold uppercase leading-none">This part of the gym is not on the map.</h1><p className="mt-5 text-sm leading-7 text-muted-foreground">The route may be misspelled, moved to a canonical address, or not built yet.</p><Link className="mt-7 inline-flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-extrabold text-primary-foreground" to="/"><ArrowLeft className="size-4" aria-hidden /> Back home</Link></section></main>
  </AppFrame>;
}
