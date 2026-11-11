import { useState } from "react";
import type { ReactNode } from "react";
import type { ClientInfo } from "../api/types";
import { copyText } from "../lib/util";

export function Spinner({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function YouTubeIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden>
      <path
        fill="currentColor"
        d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8ZM9.6 15.6V8.4l6.2 3.6-6.2 3.6Z"
      />
    </svg>
  );
}

export function SoundIcon({ muted }: { muted: boolean }) {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M11 5 6 9H3v6h3l5 4V5Z" />
      {muted ? <path d="m22 9-6 6M16 9l6 6" /> : <path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13" />}
    </svg>
  );
}

/** Client logo (or initials) and name. */
export function BrandHeader({ client, right }: { client: ClientInfo; right?: ReactNode }) {
  const initials = client.name.split(/\s+/).slice(0, 2).map((word) => word[0]).join("").toUpperCase();
  return (
    <header className="flex w-full items-center justify-between gap-3 py-4">
      <div className="flex min-w-0 items-center gap-3">
        {client.logo_url ? (
          <img src={client.logo_url} alt="" className="h-11 w-11 rounded-2xl object-cover" />
        ) : (
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-accent to-brand font-display text-lg font-extrabold text-ink shadow-lg">
            {initials}
          </div>
        )}
        <div className="min-w-0">
          <p className="truncate font-display text-lg font-bold leading-tight">{client.name}</p>
          {client.tagline && <p className="truncate text-xs text-white/55">{client.tagline}</p>}
        </div>
      </div>
      {right}
    </header>
  );
}

/** Read-only value with a copy button. */
export function CopyField({ value, label, mono = false }: { value: string; label: string; mono?: boolean }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    if (await copyText(value)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    }
  };
  return (
    <div className="flex items-stretch gap-2">
      <div
        className={`min-w-0 flex-1 truncate rounded-xl border border-white/15 bg-black/25 px-3.5 py-3 text-sm ${
          mono ? "font-mono tracking-wider" : ""
        }`}
        title={value}
      >
        {value}
      </div>
      <button type="button" onClick={copy} className="btn-ghost min-w-[84px] px-3 text-sm" aria-label={`Copy ${label}`}>
        {copied ? "Copied ✓" : "Copy"}
      </button>
    </div>
  );
}

/** Centered full-page message for loading / error / empty states. */
export function PageMessage({ icon, title, children }: { icon: ReactNode; title: string; children?: ReactNode }) {
  return (
    <main className="app-bg grid min-h-[100dvh] place-items-center px-6 text-center">
      <div className="max-w-sm">
        <div className="mb-4 flex justify-center text-5xl">{icon}</div>
        <h1 className="font-display text-2xl font-bold">{title}</h1>
        {children && <div className="mt-2 space-y-4 text-sm text-white/65">{children}</div>}
      </div>
    </main>
  );
}
