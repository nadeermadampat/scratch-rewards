import type { ReactNode } from "react";

/** One numbered step in the landing-page journey. */
export function Step({ number, title, done, children }: { number: number; title: string; done?: boolean; children: ReactNode }) {
  return (
    <li className="flex gap-3.5">
      <div
        className={`mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm font-bold ${
          done ? "bg-emerald-400 text-ink" : "bg-white/10 text-white ring-1 ring-white/20"
        }`}
        aria-hidden
      >
        {done ? "✓" : number}
      </div>
      <div className="min-w-0 flex-1">
        <h3 className="font-display text-lg font-bold leading-tight">{title}</h3>
        <div className="mt-2.5">{children}</div>
      </div>
    </li>
  );
}
