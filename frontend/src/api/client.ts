import type {
  AdminCampaign,
  AdminOverview,
  AuthorizeResult,
  Campaign,
  CampaignSummary,
  IssuedCard,
  ParticipantPayload,
  RedeemResult,
  ScratchCardView,
  VerifyPayload,
  VerifyResult,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

/** Calls the API and unwraps the `{success, data | error}` envelope. */
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init.headers },
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Can't reach the server. Check your connection and try again.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok || !body?.success) {
    throw new ApiError(
      response.status,
      body?.error?.code ?? "UNKNOWN",
      body?.error?.message ?? "Something went wrong. Please try again.",
    );
  }
  return body.data as T;
}

const post = (body?: unknown): RequestInit => ({
  method: "POST",
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  listCampaigns: () => request<CampaignSummary[]>("/campaigns"),
  getCampaign: (idOrSlug: string) => request<Campaign>(`/campaigns/${encodeURIComponent(idOrSlug)}`),
  verify: (payload: VerifyPayload) => request<VerifyResult>("/subscriptions/verify", post(payload)),
  authorize: (payload: ParticipantPayload) => request<AuthorizeResult>("/subscriptions/authorize", post(payload)),
  completeOAuth: (state: string, code: string) =>
    request<VerifyResult>("/subscriptions/oauth/complete", post({ state, code })),
  issueCard: (verificationToken: string) =>
    request<IssuedCard>("/scratch-cards", post({ verification_token: verificationToken })),
  getCard: (token: string) => request<ScratchCardView>(`/scratch-cards/${encodeURIComponent(token)}`),
  startCard: (token: string) =>
    request<ScratchCardView>(`/scratch-cards/${encodeURIComponent(token)}/start`, post()),
  replayCard: (token: string) =>
    request<ScratchCardView>(`/scratch-cards/${encodeURIComponent(token)}/replay`, post()),
  completeCard: (token: string) =>
    request<ScratchCardView>(`/scratch-cards/${encodeURIComponent(token)}/complete`, post()),
};

export function adminApi(key: string) {
  const auth = (init: RequestInit = {}): RequestInit => ({ ...init, headers: { "X-Admin-Key": key } });
  const patch = (body: unknown): RequestInit => ({ method: "PATCH", body: JSON.stringify(body) });
  return {
    overview: (campaignId?: string) =>
      request<AdminOverview>(`/admin/overview${campaignId ? `?campaign_id=${campaignId}` : ""}`, auth()),
    campaigns: () => request<AdminCampaign[]>("/admin/campaigns", auth()),
    updateCampaign: (id: string, changes: { status?: string; max_cards_per_user?: number }) =>
      request<AdminCampaign>(`/admin/campaigns/${id}`, auth(patch(changes))),
    updateReward: (id: string, changes: { weight?: number; is_active?: boolean }) =>
      request<unknown>(`/admin/rewards/${id}`, auth(patch(changes))),
    redeem: (claimReference: string) =>
      request<RedeemResult>("/admin/redemptions", auth(post({ claim_reference: claimReference }))),
  };
}

export type AdminApi = ReturnType<typeof adminApi>;
