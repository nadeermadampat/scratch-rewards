// Mirrors backend/app/schemas. The backend is the source of truth.

export interface Brand {
  primary: string;
  accent: string;
}

export interface ClientInfo {
  name: string;
  slug: string;
  tagline: string | null;
  logo_url: string | null;
  brand: Brand;
}

export interface Platform {
  key: string;
  display_name: string;
  action_label: string;
  brand_color: string;
  enabled: boolean;
  /** "simulated" | "oauth" | "unavailable" */
  verification_mode: string;
  /** In oauth mode: signing in also subscribes the account if needed. */
  auto_subscribe: boolean;
}

export interface CampaignSummary {
  id: string;
  slug: string;
  name: string;
  headline: string | null;
  client_name: string;
  platform: string;
}

export interface Campaign {
  id: string;
  slug: string;
  name: string;
  headline: string | null;
  description: string | null;
  terms: string | null;
  status: string;
  is_open: boolean;
  starts_at: string | null;
  ends_at: string | null;
  client: ClientInfo;
  platform: Platform;
  engagement: { url: string; title: string; handle: string | null; instructions: string[] };
  prizes: { name: string; icon: string | null }[];
  scratch: { reveal_threshold: number; expiry_hours: number };
}

export interface ParticipantPayload {
  campaign_id: string;
  device_id: string;
  name?: string;
  email?: string;
  consent: boolean;
}

export interface VerifyPayload extends ParticipantPayload {
  proof: Record<string, unknown>;
}

export interface AuthorizeResult {
  authorization_url: string;
  state: string;
}

export interface VerifyResult {
  verification_id: string;
  status: "verified" | "failed" | "pending";
  method: string;
  message: string | null;
  verification_token: string | null;
  expires_at: string | null;
  campaign_slug: string | null;
}

export interface IssuedCard {
  token: string;
  url: string;
  expires_at: string;
  existing: boolean;
}

export interface Reward {
  id: string;
  name: string;
  description: string | null;
  reward_type: string;
  value: string | null;
  icon: string | null;
  is_prize: boolean;
  redemption_instructions: string | null;
}

export type CardStatus = "issued" | "opened" | "scratching" | "completed" | "expired";

export interface ScratchCardView {
  reference: string;
  status: CardStatus;
  campaign: { name: string; slug: string; client: ClientInfo };
  reveal_threshold: number;
  generated_at: string;
  expires_at: string;
  scratch_started_at: string | null;
  scratch_completed_at: string | null;
  reward: Reward | null;
  claim_reference: string | null;
  redemption_status: "not_applicable" | "pending" | "redeemed";
  already_completed: boolean;
}

// -- admin ----------------------------------------------------------------

export interface AdminStats {
  total_users: number;
  cards_generated: number;
  cards_scratched: number;
  rewards_distributed: number;
  rewards_redeemed: number;
  verifications_failed: number;
}

export interface RewardDistribution {
  reward_id: string;
  name: string;
  icon: string | null;
  is_prize: boolean;
  is_active: boolean;
  weight: number;
  configured_share: number;
  total_quantity: number | null;
  assigned: number;
  revealed: number;
}

export interface Activity {
  card_reference: string;
  user_label: string;
  campaign_name: string;
  status: CardStatus;
  reward_name: string | null;
  claim_reference: string | null;
  redemption_status: string;
  generated_at: string;
  completed_at: string | null;
}

export interface AdminOverview {
  stats: AdminStats;
  distribution: RewardDistribution[];
  recent_activity: Activity[];
}

export interface AdminCampaign {
  id: string;
  slug: string;
  name: string;
  client_name: string;
  platform: string;
  status: "draft" | "active" | "paused" | "ended";
  starts_at: string | null;
  ends_at: string | null;
}

export interface RedeemResult {
  claim_reference: string;
  reward_name: string;
  redemption_status: string;
  redeemed_at: string | null;
}
