import { useCallback, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Campaign, IssuedCard } from "../api/types";
import { getDeviceId, sleep } from "../lib/util";

export type FlowStatus = "idle" | "verifying" | "issuing" | "ready";

export interface ParticipantDetails {
  name: string;
  email: string;
  consent: boolean;
}

/** Landing-page journey: open the channel -> verify -> receive a scratch card. */
export function useEngagementFlow(campaign: Campaign) {
  const [visitedChannel, setVisitedChannel] = useState(false);
  const [status, setStatus] = useState<FlowStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [card, setCard] = useState<IssuedCard | null>(null);

  const markVisited = useCallback(() => setVisitedChannel(true), []);

  const submit = useCallback(
    async (details: ParticipantDetails) => {
      setError(null);
      setStatus("verifying");
      try {
        const [verification] = await Promise.all([
          api.verify({
            campaign_id: campaign.id,
            device_id: getDeviceId(),
            name: details.name || undefined,
            email: details.email || undefined,
            consent: details.consent,
            // Simulated mode accepts the participant's confirmation. A real provider
            // would put its evidence here instead (e.g. an OAuth authorization code).
            proof: { attested: visitedChannel },
          }),
          sleep(1100), // keep the "checking" state visible long enough to read
        ]);
        if (verification.status !== "verified" || !verification.verification_token) {
          setError(verification.message ?? "We couldn't verify your subscription yet. Please try again.");
          setStatus("idle");
          return;
        }
        setStatus("issuing");
        setCard(await api.issueCard(verification.verification_token));
        setStatus("ready");
      } catch (e) {
        setError((e as ApiError).message);
        setStatus("idle");
      }
    },
    [campaign.id, visitedChannel],
  );

  return { visitedChannel, markVisited, status, error, card, submit };
}
