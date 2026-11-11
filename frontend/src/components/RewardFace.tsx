import { motion } from "framer-motion";
import type { Reward } from "../api/types";

/** What sits under the coating. Until the reward arrives it is a neutral foil backing. */
export function RewardFace({ reward, revealed }: { reward: Reward | null; revealed: boolean }) {
  const prize = reward?.is_prize ?? true;
  return (
    <div
      className={`absolute inset-0 grid place-items-center overflow-hidden text-ink ${
        prize
          ? "bg-gradient-to-br from-amber-200 via-yellow-300 to-amber-400"
          : "bg-gradient-to-br from-slate-200 via-indigo-100 to-slate-300"
      }`}
    >
      {/* Sunburst */}
      <div
        aria-hidden
        className="absolute left-1/2 top-1/2 aspect-square w-[170%] -translate-x-1/2 -translate-y-1/2 opacity-40"
        style={{
          background:
            "repeating-conic-gradient(from 0deg, rgba(255,255,255,0.9) 0deg 9deg, rgba(255,255,255,0) 9deg 18deg)",
        }}
      />
      {reward && (
        <motion.div
          className="relative flex flex-col items-center px-4 text-center"
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: revealed ? [1, 1.12, 1] : 1 }}
          transition={{ duration: revealed ? 0.6 : 0.25 }}
        >
          <span className="text-[clamp(2.4rem,13vw,3.6rem)] leading-none drop-shadow-sm">{reward.icon ?? "🎁"}</span>
          {reward.value && prize && (
            <span className="mt-1 font-display text-[clamp(1.9rem,10vw,2.8rem)] font-extrabold leading-none">
              {reward.value}
            </span>
          )}
          <span className="mt-1 font-display text-[clamp(1rem,5vw,1.3rem)] font-bold leading-tight">{reward.name}</span>
        </motion.div>
      )}
    </div>
  );
}
