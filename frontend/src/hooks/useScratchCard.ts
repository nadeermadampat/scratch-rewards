import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ScratchCardView } from "../api/types";
import { sleep } from "../lib/util";

/**
 * UI phases of a scratch card.
 *  initial    – fully covered
 *  scratching – finger/mouse is down
 *  partial    – some coating removed, not yet at the threshold
 *  revealed   – threshold reached; coating clears while the result is saved
 *  completed  – the server has recorded the completion and issued the claim reference
 */
export type Phase =
  | "loading" | "initial" | "scratching" | "partial" | "revealed" | "completed"
  | "expired" | "not_found" | "error";

/**
 * Server-backed state machine for one card. All outcomes come from the API.
 *
 * A finished card can be *replayed*: the coating comes back and the participant
 * scratches again to see the same, already-recorded result. Replays change nothing
 * on the server except a tracking event.
 */
export function useScratchCard(token: string, replayOnLoad: boolean) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [card, setCard] = useState<ScratchCardView | null>(null);
  const [error, setError] = useState<string | null>(null);
  /** True only when the reveal happened in this visit (drives confetti and sound). */
  const [revealedNow, setRevealedNow] = useState(false);
  /** > 0 while (or after) scratching a finished card again; changes on every replay. */
  const [replayRound, setReplayRound] = useState(0);
  const startRequest = useRef<Promise<ScratchCardView> | null>(null);
  const revealing = useRef(false);
  const replaying = useRef(false);
  const replayOnLoadRef = useRef(replayOnLoad);

  const startReplay = useCallback(() => {
    replaying.current = true;
    revealing.current = false;
    setRevealedNow(false);
    setError(null);
    setReplayRound((round) => round + 1);
    setPhase("initial");
  }, []);

  useEffect(() => {
    let alive = true;
    startRequest.current = null;
    revealing.current = false;
    replaying.current = false;
    setPhase("loading");
    api.getCard(token)
      .then((loaded) => {
        if (!alive) return;
        setCard(loaded);
        if (loaded.status === "expired") setPhase("expired");
        else if (loaded.status !== "completed") setPhase("initial");
        else if (replayOnLoadRef.current) startReplay();
        else setPhase("completed");
      })
      .catch((e: ApiError) => {
        if (!alive) return;
        setError(e.message);
        setPhase(e.status === 404 ? "not_found" : "error");
      });
    return () => {
      alive = false;
    };
  }, [token, startReplay]);

  const fail = useCallback((e: ApiError) => {
    if (e.code === "CARD_EXPIRED") setPhase("expired");
    else setError(e.message);
  }, []);

  /** Tell the server scratching began; its response carries the pre-assigned reward. */
  const ensureStarted = useCallback((): Promise<ScratchCardView> => {
    if (!startRequest.current) {
      setError(null);
      startRequest.current = api.startCard(token)
        .then((started) => {
          setCard(started);
          if (started.status === "completed") setPhase("completed");
          return started;
        })
        .catch((e: ApiError) => {
          startRequest.current = null; // allow a retry on the next stroke
          fail(e);
          throw e;
        });
    }
    return startRequest.current;
  }, [token, fail]);

  const beginScratch = useCallback(() => {
    if (replaying.current) return; // the result is already recorded
    ensureStarted().catch(() => undefined);
  }, [ensureStarted]);

  const setStroking = useCallback((active: boolean) => {
    setPhase((current) =>
      current === "initial" || current === "scratching" || current === "partial"
        ? active ? "scratching" : "partial"
        : current,
    );
  }, []);

  const complete = useCallback(async () => {
    setError(null);
    for (let attempt = 0; ; attempt++) {
      try {
        setCard(await api.completeCard(token)); // idempotent on the server, safe to retry
        setPhase("completed");
        return;
      } catch (e) {
        const apiError = e as ApiError;
        const retryable = apiError.status === 0 || apiError.status === 429 || apiError.status >= 500;
        if (!retryable || attempt >= 2) {
          fail(apiError);
          return;
        }
        await sleep(700 * (attempt + 1));
      }
    }
  }, [token, fail]);

  const reveal = useCallback(() => {
    if (revealing.current) return;
    revealing.current = true;
    setRevealedNow(true);
    if (replaying.current) {
      setPhase("completed");
      api.replayCard(token).catch(() => undefined); // tracking only; never blocks the reveal
      return;
    }
    setPhase("revealed");
    void complete();
  }, [complete, token]);

  /** Accessible alternative to scratching. */
  const revealWithoutScratching = useCallback(async () => {
    if (replaying.current) {
      reveal();
      return;
    }
    try {
      const started = await ensureStarted();
      if (started.status !== "completed") reveal();
    } catch {
      /* surfaced through `error` / `phase` */
    }
  }, [ensureStarted, reveal]);

  return {
    phase, card, error, revealedNow, replayRound,
    beginScratch, setStroking, reveal, retrySave: complete, revealWithoutScratching, startReplay,
  };
}
