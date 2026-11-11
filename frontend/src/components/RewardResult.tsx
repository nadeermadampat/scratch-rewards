import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import type { ScratchCardView } from "../api/types";
import { formatDateTime } from "../lib/util";
import { CopyField } from "./ui";

/** Result details shown once the server has recorded the completion. */
export function RewardResult({ card }: { card: ScratchCardView }) {
  const reward = card.reward;
  if (!reward) return null;

  return (
    <motion.section
      className="panel mt-5 w-full p-5"
      initial={{ opacity: 0, y: 28 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 180, damping: 20, delay: 0.25 }}
      aria-live="polite"
    >
      {reward.is_prize ? (
        <>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Your reward</p>
          <h2 className="mt-1 font-display text-2xl font-extrabold leading-tight">{reward.name}</h2>
          {reward.description && <p className="mt-1 text-sm text-white/70">{reward.description}</p>}

          <div className="mt-5">
            <p className="mb-1.5 text-xs font-medium text-white/55">Claim reference</p>
            {card.claim_reference && <CopyField value={card.claim_reference} label="claim reference" mono />}
          </div>

          {reward.redemption_instructions && (
            <div className="mt-4 rounded-2xl bg-white/[0.06] p-4">
              <p className="text-sm font-semibold">How to redeem</p>
              <p className="mt-1 text-sm text-white/70">{reward.redemption_instructions}</p>
            </div>
          )}

          <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
            <div>
              <dt className="text-white/45">Won on</dt>
              <dd className="mt-0.5 font-medium">{formatDateTime(card.scratch_completed_at)}</dd>
            </div>
            <div>
              <dt className="text-white/45">Status</dt>
              <dd className="mt-0.5 font-medium">
                {card.redemption_status === "redeemed" ? "✓ Redeemed" : "● Ready to redeem"}
              </dd>
            </div>
          </dl>
          <p className="mt-4 text-xs text-white/45">
            Take a screenshot or save this page link — it is the only way back to your reward.
          </p>
        </>
      ) : (
        <>
          <h2 className="font-display text-2xl font-extrabold leading-tight">No prize this time</h2>
          <p className="mt-1 text-sm text-white/70">
            {reward.description ?? "Thanks for taking part!"} Keep an eye on {card.campaign.client.name} for the
            next giveaway.
          </p>
          {card.claim_reference && (
            <p className="mt-3 text-xs text-white/45">Reference: {card.claim_reference}</p>
          )}
        </>
      )}
      <Link to={`/c/${card.campaign.slug}`} className="btn-ghost mt-5 w-full">
        Back to {card.campaign.name}
      </Link>
    </motion.section>
  );
}
