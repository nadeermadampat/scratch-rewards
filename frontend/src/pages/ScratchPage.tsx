import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Confetti } from "../components/Confetti";
import { RewardFace } from "../components/RewardFace";
import { RewardResult } from "../components/RewardResult";
import { ScratchCard } from "../components/ScratchCard";
import { BrandHeader, PageMessage, SoundIcon, Spinner } from "../components/ui";
import { useScratchCard } from "../hooks/useScratchCard";
import type { Phase } from "../hooks/useScratchCard";
import { ScratchAudio } from "../lib/scratch/audio";
import { applyBrand, timeLeft } from "../lib/util";

function heading(phase: Phase, isPrize: boolean | undefined): string {
  switch (phase) {
    case "scratching":
    case "partial":
      return "Keep scratching…";
    case "revealed":
      return "Here it comes…";
    case "completed":
      return isPrize ? "Congratulations! 🎉" : "Better luck next time";
    default:
      return "Scratch to reveal your surprise!";
  }
}

export function ScratchPage() {
  const { token = "" } = useParams();
  const { phase, card, error, revealedNow, beginScratch, setStroking, reveal, retrySave, revealWithoutScratching } =
    useScratchCard(token);
  const audio = useMemo(() => new ScratchAudio(), []);
  const [muted, setMuted] = useState(audio.muted);
  const [progress, setProgress] = useState(0);

  useEffect(() => applyBrand(card?.campaign.client.brand), [card?.campaign.client.brand]);

  // Jingle + haptic tick at the moment of reveal (never on a refresh of a finished card).
  const isPrize = card?.reward?.is_prize;
  useEffect(() => {
    if (!revealedNow) return;
    if (isPrize) audio.playWin();
    else audio.playNoWin();
    navigator.vibrate?.(isPrize ? [30, 40, 60] : 20);
  }, [revealedNow, isPrize, audio]);

  if (phase === "loading") {
    return <PageMessage icon={<Spinner className="h-10 w-10" />} title="Getting your card ready…" />;
  }
  if (phase === "not_found") {
    return (
      <PageMessage icon="🔍" title="We can't find this scratch card">
        <p>The link may be incomplete. Open it again from the original message, or start over.</p>
        <Link to="/" className="btn-primary">See current campaigns</Link>
      </PageMessage>
    );
  }
  if (!card || phase === "error") {
    return (
      <PageMessage icon="⚠️" title="Your card didn't load">
        <p>{error}</p>
        <button className="btn-primary" onClick={() => window.location.reload()}>Try again</button>
      </PageMessage>
    );
  }
  if (phase === "expired") {
    return (
      <PageMessage icon="⌛" title="This scratch card has expired">
        <p>Cards are only valid for a limited time after they are issued.</p>
        <Link to={`/c/${card.campaign.slug}`} className="btn-primary">Back to {card.campaign.name}</Link>
      </PageMessage>
    );
  }

  const cleared = phase === "revealed" || phase === "completed";
  const toThreshold = Math.min(1, progress / card.reveal_threshold);
  const toggleMute = () => {
    audio.setMuted(!muted);
    setMuted(!muted);
  };

  return (
    <main className="app-bg min-h-[100dvh] overflow-x-hidden overscroll-none">
      <Confetti fire={revealedNow && isPrize === true} />
      <div className="mx-auto flex w-full max-w-md flex-col items-center px-4 pb-10">
        <BrandHeader
          client={card.campaign.client}
          right={
            <button
              type="button"
              onClick={toggleMute}
              aria-pressed={muted}
              aria-label={muted ? "Turn sound on" : "Turn sound off"}
              className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-white/15 bg-white/[0.07] text-white/80"
            >
              <SoundIcon muted={muted} />
            </button>
          }
        />

        <motion.h1
          key={heading(phase, isPrize)}
          className="mt-2 min-h-[2.6em] text-balance text-center font-display text-[1.7rem] font-extrabold leading-tight"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          {heading(phase, isPrize)}
        </motion.h1>

        {/* Ticket */}
        <motion.div
          className="mt-3 w-full rounded-[28px] bg-gradient-to-b from-white/[0.16] to-white/[0.05] p-3 shadow-card ring-1 ring-white/15"
          initial={{ opacity: 0, y: 24, rotate: -1.5 }}
          animate={{ opacity: 1, y: 0, rotate: 0 }}
          transition={{ type: "spring", stiffness: 160, damping: 18 }}
        >
          <div className="flex items-center justify-between px-2 pb-2.5 pt-1 text-xs">
            <span className="font-semibold uppercase tracking-[0.16em] text-accent">{card.campaign.name}</span>
            <span className="font-mono text-white/45">#{card.reference}</span>
          </div>
          <ScratchCard
            threshold={card.reveal_threshold}
            cleared={cleared}
            ready={card.reward !== null}
            audio={audio}
            onFirstScratch={beginScratch}
            onStrokeChange={setStroking}
            onProgress={setProgress}
            onThreshold={reveal}
          >
            <RewardFace reward={card.reward} revealed={cleared} />
          </ScratchCard>

          {!cleared && (
            <div className="px-2 pb-1 pt-3">
              <div
                className="h-1.5 overflow-hidden rounded-full bg-white/10"
                role="progressbar"
                aria-label="Scratch progress"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(toThreshold * 100)}
              >
                <div
                  className="h-full rounded-full bg-accent transition-[width] duration-150"
                  style={{ width: `${toThreshold * 100}%` }}
                />
              </div>
              <p className="mt-2 text-center text-xs text-white/55">
                {progress === 0
                  ? `Scratch about ${Math.round(card.reveal_threshold * 100)}% of the card to reveal your result`
                  : "Almost there — keep going!"}
              </p>
            </div>
          )}
        </motion.div>

        {error && (
          <div role="alert" className="mt-4 w-full rounded-2xl border border-red-400/40 bg-red-500/15 p-4 text-sm">
            <p>{error}</p>
            {phase === "revealed" && (
              <button className="btn-ghost mt-3 w-full" onClick={() => void retrySave()}>
                Try saving again
              </button>
            )}
          </div>
        )}

        {phase === "revealed" && !error && (
          <p className="mt-4 flex items-center gap-2 text-sm text-white/60">
            <Spinner className="h-4 w-4" /> Saving your result…
          </p>
        )}

        {phase === "completed" && <RewardResult card={card} />}

        {!cleared && (
          <div className="mt-5 flex flex-col items-center gap-2 text-xs text-white/45">
            <p>Card expires in {timeLeft(card.expires_at)}</p>
            <button
              type="button"
              className="rounded-lg px-3 py-2 underline underline-offset-4 hover:text-white/80"
              onClick={() => void revealWithoutScratching()}
            >
              Can't scratch? Reveal my result
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
