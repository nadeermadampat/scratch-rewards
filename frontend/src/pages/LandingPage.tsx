import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Campaign, IssuedCard } from "../api/types";
import { OAuthSteps } from "../components/OAuthSteps";
import { Step } from "../components/Step";
import { BrandHeader, CopyField, PageMessage, Spinner, YouTubeIcon } from "../components/ui";
import { useEngagementFlow } from "../hooks/useEngagementFlow";
import { applyBrand, timeLeft } from "../lib/util";

export function LandingPage() {
  const { slug = "" } = useParams();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    let alive = true;
    setCampaign(null);
    setError(null);
    api.getCampaign(slug)
      .then((loaded) => {
        if (!alive) return;
        applyBrand(loaded.client.brand);
        document.title = `${loaded.name} · ${loaded.client.name}`;
        setCampaign(loaded);
      })
      .catch((e: ApiError) => alive && setError(e));
    return () => {
      alive = false;
    };
  }, [slug]);

  if (error) {
    return (
      <PageMessage icon={error.status === 404 ? "🔍" : "⚠️"} title={error.status === 404 ? "Campaign not found" : "This page didn't load"}>
        <p>{error.message}</p>
        <Link to="/" className="btn-primary">See current campaigns</Link>
      </PageMessage>
    );
  }
  if (!campaign) return <PageMessage icon={<Spinner className="h-10 w-10" />} title="Loading…" />;

  return (
    <main className="app-bg min-h-[100dvh]">
      <div className="mx-auto w-full max-w-md px-4 pb-12">
        <BrandHeader client={campaign.client} />

        <motion.section
          className="pt-3 text-center"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className="mx-auto mb-3 w-fit animate-floaty text-6xl drop-shadow-[0_10px_24px_rgb(var(--accent)/0.5)]">🎁</div>
          <h1 className="text-balance font-display text-[2.1rem] font-extrabold leading-[1.1]">
            {campaign.headline ?? campaign.name}
          </h1>
          {campaign.description && <p className="mt-3 text-[15px] leading-relaxed text-white/70">{campaign.description}</p>}
        </motion.section>

        {campaign.prizes.length > 0 && (
          <section className="mt-6" aria-label="Prizes">
            <p className="mb-2 text-center text-xs font-semibold uppercase tracking-[0.18em] text-white/45">You could win</p>
            <ul className="flex flex-wrap justify-center gap-2">
              {campaign.prizes.map((prize) => (
                <li key={prize.name} className="rounded-full border border-white/10 bg-white/[0.07] px-3 py-1.5 text-sm">
                  <span className="mr-1.5">{prize.icon}</span>
                  {prize.name}
                </li>
              ))}
            </ul>
          </section>
        )}

        {campaign.is_open && campaign.platform.enabled ? (
          campaign.platform.verification_mode === "oauth" ? (
            <OAuthSteps campaign={campaign} />
          ) : (
            <EngagementSteps campaign={campaign} />
          )
        ) : (
          <div className="panel mt-7 p-6 text-center">
            <p className="text-3xl">⏸️</p>
            <h2 className="mt-2 font-display text-xl font-bold">This campaign isn't running right now</h2>
            <p className="mt-1 text-sm text-white/65">Follow {campaign.client.name} to hear about the next one.</p>
          </div>
        )}

        {campaign.terms && (
          <details className="mt-6 rounded-2xl border border-white/10 px-4 py-3 text-sm text-white/60">
            <summary className="cursor-pointer font-medium text-white/80">Terms & privacy</summary>
            <p className="mt-2 leading-relaxed">{campaign.terms}</p>
            <p className="mt-2 leading-relaxed">
              Your name and email are optional. We store what you enter, an anonymous browser id and your scratch
              card result, only to run this promotion and prevent duplicate entries.
            </p>
          </details>
        )}
      </div>
    </main>
  );
}

function EngagementSteps({ campaign }: { campaign: Campaign }) {
  const flow = useEngagementFlow(campaign);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const { platform, engagement } = campaign;
  const busy = flow.status === "verifying" || flow.status === "issuing";

  if (flow.status === "ready" && flow.card) return <CardReady card={flow.card} />;

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    void flow.submit({ name: name.trim(), email: email.trim(), consent });
  };

  return (
    <motion.form
      onSubmit={onSubmit}
      className="panel mt-7 p-5"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15, duration: 0.4 }}
    >
      <ol className="space-y-6">
        <Step number={1} title={`${platform.action_label} to ${engagement.title} on ${platform.display_name}`} done={flow.visitedChannel}>
          <a
            href={engagement.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={flow.markVisited}
            className="btn w-full text-white hover:brightness-110"
            style={{ backgroundColor: platform.brand_color }}
          >
            <YouTubeIcon /> {platform.action_label} on {platform.display_name}
          </a>
          <p className="mt-2 text-xs text-white/50">
            Opens {platform.display_name} in a new tab. Confirm the subscription there, then come back here.
          </p>
        </Step>

        <Step number={2} title="Tell us who you are (optional)">
          <div className="space-y-2.5">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-white/60">Name</span>
              <input className="field" value={name} onChange={(e) => setName(e.target.value)} maxLength={120} autoComplete="name" placeholder="Asha Menon" />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-white/60">Email</span>
              <input className="field" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" inputMode="email" placeholder="asha@example.com" />
            </label>
          </div>
        </Step>

        <Step number={3} title="Verify and get your scratch card">
          <label className="flex cursor-pointer items-start gap-3 text-sm text-white/75">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-0.5 h-5 w-5 shrink-0 rounded accent-[rgb(var(--accent))]"
            />
            <span>I agree to the campaign terms and to my details being stored to run this promotion.</span>
          </label>

          {flow.error && (
            <p role="alert" className="mt-3 rounded-xl border border-red-400/40 bg-red-500/15 px-3.5 py-2.5 text-sm">
              {flow.error}
            </p>
          )}

          <button type="submit" className="btn-primary mt-4 w-full" disabled={busy || !consent || !flow.visitedChannel}>
            {flow.status === "verifying" && (<><Spinner /> Checking your subscription…</>)}
            {flow.status === "issuing" && (<><Spinner /> Creating your scratch card…</>)}
            {flow.status === "idle" && "I've subscribed — verify"}
          </button>
          {!busy && (!flow.visitedChannel || !consent) && (
            <p className="mt-2 text-center text-xs text-white/45">
              {!flow.visitedChannel ? `${platform.action_label} in step 1 first.` : "Tick the box above to continue."}
            </p>
          )}
        </Step>
      </ol>

      {platform.verification_mode === "simulated" && (
        <p className="mt-5 rounded-xl bg-white/[0.06] px-3.5 py-2.5 text-xs text-white/55">
          <strong className="text-white/75">Demo mode:</strong> subscription checks are simulated. We take your word
          for it rather than checking with {platform.display_name}.
        </p>
      )}
    </motion.form>
  );
}

function CardReady({ card }: { card: IssuedCard }) {
  return (
    <motion.section
      className="panel mt-7 p-6 text-center"
      initial={{ opacity: 0, scale: 0.94 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: "spring", stiffness: 200, damping: 18 }}
      aria-live="polite"
    >
      <motion.div className="text-6xl" initial={{ rotate: -20, scale: 0.5 }} animate={{ rotate: 0, scale: 1 }} transition={{ type: "spring", stiffness: 220, damping: 10 }}>
        🎟️
      </motion.div>
      <h2 className="mt-3 font-display text-2xl font-extrabold">
        {card.existing ? "You already have a scratch card" : "Your scratch card is ready!"}
      </h2>
      <p className="mt-1 text-sm text-white/65">
        {card.existing
          ? "It's one card per person. You can scratch yours again; the result stays the same."
          : `Thanks for subscribing. It expires in ${timeLeft(card.expires_at)}.`}
      </p>
      <Link to={`/s/${card.token}`} state={{ replay: true }} className="btn-primary mt-5 w-full text-base">
        Open my scratch card
      </Link>
      <div className="mt-5 text-left">
        <p className="mb-1.5 text-xs font-medium text-white/55">Your personal link — best opened on your phone</p>
        <CopyField value={card.url} label="scratch card link" />
        <p className="mt-2 text-xs text-white/45">Keep it private: anyone with this link can scratch your card.</p>
      </div>
    </motion.section>
  );
}
