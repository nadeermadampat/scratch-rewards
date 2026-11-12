import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { Confetti } from "../components/Confetti";
import { RewardFace } from "../components/RewardFace";
import { RewardResult } from "../components/RewardResult";
import { ScratchCard } from "../components/ScratchCard";
import { BrandHeader, PageMessage, SoundIcon, Spinner } from "../components/ui";
import { useScratchCard } from "../hooks/useScratchCard";
import type { Phase } from "../hooks/useScratchCard";
import { ScratchAudio } from "../lib/scratch/audio";
import { applyBrand, formatDateTime, timeLeft } from "../lib/util";

function heading(phase: Phase, isPrize: boolean | undefined, revealedNow: boolean, isReplay: boolean): string {
  switch (phase) {
    case "initial":
      return isReplay ? "Scratch again to see your reward!" : "Scratch to reveal your surprise!";
    case "scratching":
    case "partial":
      return "Keep scratching…";
    case "revealed":
      return "Here it comes…";
    case "completed":
      if (!revealedNow) return "Your scratch card result";
      return isPrize ? "Congratulations! 🎉" : "Better luck next time";
    default:
      return "Scratch to reveal your surprise!";
  }
}

export function ScratchPage() {
  const { token = "" } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  // Set when the participant arrives from the campaign flow: they should always get to scratch.
  const arrivedFromCampaign = (location.state as { replay?: boolean } | null)?.replay === true;
  const {
    phase, card, error, revealedNow, replayRound,
    beginScratch, setStroking, reveal, retrySave, revealWithoutScratching, startReplay,
  } = useScratchCard(token, arrivedFromCampaign);
  const isReplay = replayRound > 0;
  const audio = useMemo(() => new ScratchAudio(), []);
  const [muted, setMuted] = useState(audio.muted);
  const [progress, setProgress] = useState(0);

  // A new replay starts from a fresh coating.
  useEffect(() => setProgress(0), [replayRound]);

  // Once revealed, forget the "arrived from campaign" marker so a refresh shows the result.
  useEffect(() => {
    if (revealedNow && arrivedFromCampaign) navigate(location.pathname, { replace: true, state: null });
  }, [revealedNow, arrivedFromCampaign, navigate, location.pathname]);

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

  // overflow-x-clip (not hidden): hidden would turn <main> into a scroll container and trap page scrolling.
  return (
    <main className="app-bg min-h-[100dvh] overflow-x-clip">
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
          key={heading(phase, isPrize, revealedNow, isReplay)}
          className="mt-2 min-h-[2.6em] text-balance text-center font-display text-[1.7rem] font-extrabold leading-tight"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          {heading(phase, isPrize, revealedNow, isReplay)}
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
            key={replayRound} // remount: a replay gets a freshly painted coating
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

        {phase === "completed" && !revealedNow && (
          <div role="status" className="mt-4 w-full rounded-2xl border border-white/15 bg-white/[0.07] px-4 py-3 text-sm text-white/80">
            <p>
              <strong className="text-white">You've already scratched this card</strong>
              {card.scratch_completed_at ? ` on ${formatDateTime(card.scratch_completed_at)}` : ""}. Your result is
              below.
            </p>
            <button type="button" className="btn-ghost mt-3 min-h-[40px] w-full text-sm" onClick={startReplay}>
              Scratch it again
            </button>
          </div>
        )}

        {phase === "completed" && revealedNow && isReplay && (
          <p role="status" className="mt-4 w-full rounded-2xl border border-white/15 bg-white/[0.07] px-4 py-3 text-sm text-white/80">
            This is the same result as your first scratch
            {card.scratch_completed_at ? ` on ${formatDateTime(card.scratch_completed_at)}` : ""}. It's one reward per
            person.
          </p>
        )}

        {phase === "completed" && <RewardResult card={card} />}

        {!cleared && (
          <div className="mt-5 flex flex-col items-center gap-2 text-xs text-white/45">
            {!isReplay && <p>Card expires in {timeLeft(card.expires_at)}</p>}
            <button
              type="button"
              className="rounded-lg px-3 py-2 underline underline-offset-4 hover:text-white/80"
              onClick={() => void revealWithoutScratching()}
            >
              {isReplay ? "Skip to my result" : "Can't scratch? Reveal my result"}
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
