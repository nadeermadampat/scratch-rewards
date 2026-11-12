import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { adminApi, ApiError } from "../../api/client";
import type { AdminCampaign, AdminOverview } from "../../api/types";
import { PageMessage, Spinner } from "../../components/ui";
import { ActivityTable } from "./ActivityTable";
import { RedeemBox } from "./RedeemBox";
import { RewardTable } from "./RewardTable";

const KEY_STORAGE = "sr_admin_key";

export function AdminPage() {
  const [key, setKey] = useState(() => sessionStorage.getItem(KEY_STORAGE) ?? "");
  const signOut = useCallback(() => {
    sessionStorage.removeItem(KEY_STORAGE);
    setKey("");
  }, []);
  useEffect(() => {
    document.title = "Admin · Scratch Rewards";
  }, []);
  if (!key) {
    return (
      <SignIn
        onSignedIn={(value) => {
          sessionStorage.setItem(KEY_STORAGE, value);
          setKey(value);
        }}
      />
    );
  }
  return <Dashboard adminKey={key} onSignOut={signOut} />;
}

function SignIn({ onSignedIn }: { onSignedIn: (key: string) => void }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await adminApi(value).campaigns();
      onSignedIn(value);
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="app-bg grid min-h-[100dvh] place-items-center px-4">
      <form onSubmit={submit} className="panel w-full max-w-sm p-6">
        <h1 className="font-display text-2xl font-extrabold">Admin dashboard</h1>
        <p className="mt-1 text-sm text-white/60">Enter the admin key set as ADMIN_API_KEY in your .env file.</p>
        <label className="mt-5 block">
          <span className="mb-1 block text-xs font-medium text-white/60">Admin key</span>
          <input className="field" type="password" value={value} onChange={(e) => setValue(e.target.value)} autoComplete="current-password" required />
        </label>
        {error && <p role="alert" className="mt-3 text-sm text-red-300">{error}</p>}
        <button className="btn-primary mt-5 w-full" disabled={busy || !value}>
          {busy ? <Spinner /> : "Sign in"}
        </button>
      </form>
    </main>
  );
}

function StatTile({ label, value, note }: { label: string; value: number; note?: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.05] p-4">
      <p className="text-xs font-medium text-white/55">{label}</p>
      <p className="mt-1 font-display text-3xl font-extrabold tabular-nums">{value.toLocaleString()}</p>
      {note && <p className="mt-0.5 text-xs text-white/45">{note}</p>}
    </div>
  );
}

/** How many cards one participant may receive. Raise it to re-test with the same account. */
function CardLimit({ campaign, onSave }: { campaign: AdminCampaign; onSave: (limit: number) => Promise<void> }) {
  const [value, setValue] = useState(String(campaign.max_cards_per_user));
  const parsed = Number(value);
  const valid = Number.isInteger(parsed) && parsed >= 1 && parsed <= 1000;
  const dirty = value !== String(campaign.max_cards_per_user);
  return (
    <label className="flex items-center gap-2 text-sm text-white/60" title="Raise this to get a fresh card when testing with the same account. Use 1 for a live campaign.">
      Cards per participant
      <input
        className="field w-16 px-2 py-1.5 text-sm tabular-nums"
        type="number"
        min={1}
        max={1000}
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      {dirty && (
        <button
          type="button"
          className="rounded-lg bg-accent px-2.5 py-1.5 text-xs font-semibold text-ink disabled:opacity-40"
          disabled={!valid}
          onClick={() => void onSave(parsed)}
        >
          Save
        </button>
      )}
    </label>
  );
}

const percent = (part: number, whole: number) => (whole ? `${Math.round((part / whole) * 100)}%` : "—");

function Dashboard({ adminKey, onSignOut }: { adminKey: string; onSignOut: () => void }) {
  const client = useMemo(() => adminApi(adminKey), [adminKey]);
  const [campaigns, setCampaigns] = useState<AdminCampaign[]>([]);
  const [campaignId, setCampaignId] = useState<string>("");
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await client.campaigns();
      const selected = campaignId || list[0]?.id || "";
      setCampaigns(list);
      if (selected !== campaignId) setCampaignId(selected);
      setOverview(await client.overview(selected || undefined));
      setError(null);
    } catch (e) {
      const apiError = e as ApiError;
      if (apiError.status === 401) onSignOut();
      else setError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, [client, campaignId, onSignOut]);

  useEffect(() => {
    void load();
  }, [load]);

  const campaign = campaigns.find((c) => c.id === campaignId);

  const toggleCampaign = async () => {
    if (!campaign) return;
    try {
      await client.updateCampaign(campaign.id, { status: campaign.status === "active" ? "paused" : "active" });
      await load();
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  const saveCardLimit = async (limit: number) => {
    if (!campaign) return;
    try {
      await client.updateCampaign(campaign.id, { max_cards_per_user: limit });
      await load();
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  if (!overview) {
    return error ? (
      <PageMessage icon="⚠️" title="The dashboard didn't load">
        <p>{error}</p>
        <button className="btn-primary" onClick={() => void load()}>Try again</button>
      </PageMessage>
    ) : (
      <PageMessage icon={<Spinner className="h-10 w-10" />} title="Loading dashboard…" />
    );
  }

  const { stats } = overview;
  return (
    <main className="app-bg min-h-[100dvh]">
      <div className="mx-auto w-full max-w-6xl px-4 pb-16 pt-6">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="font-display text-2xl font-extrabold">Campaign dashboard</h1>
            {campaign && <p className="text-sm text-white/55">{campaign.client_name} · {campaign.platform}</p>}
          </div>
          <div className="flex items-center gap-2">
            <button className="btn-ghost min-h-[40px] px-3.5 text-sm" onClick={() => void load()} disabled={loading}>
              {loading ? <Spinner className="h-4 w-4" /> : "Refresh"}
            </button>
            <button className="btn-ghost min-h-[40px] px-3.5 text-sm" onClick={onSignOut}>Sign out</button>
          </div>
        </header>

        {/* Filters: one row above everything they scope. */}
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-white/60">
            Campaign
            <select className="field w-auto py-2" value={campaignId} onChange={(e) => setCampaignId(e.target.value)}>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id} className="text-ink">{c.name}</option>
              ))}
            </select>
          </label>
          {campaign && (
            <>
              <span className="rounded-full border border-white/15 px-3 py-1 text-xs font-semibold">
                {campaign.status === "active" ? "▶ Active" : campaign.status === "paused" ? "⏸ Paused" : `■ ${campaign.status}`}
              </span>
              {(campaign.status === "active" || campaign.status === "paused") && (
                <button className="btn-ghost min-h-[36px] px-3 text-xs" onClick={() => void toggleCampaign()}>
                  {campaign.status === "active" ? "Pause campaign" : "Resume campaign"}
                </button>
              )}
              <CardLimit key={`${campaign.id}:${campaign.max_cards_per_user}`} campaign={campaign} onSave={saveCardLimit} />
              <a className="text-xs text-accent underline underline-offset-4" href={`/c/${campaign.slug}`} target="_blank" rel="noreferrer">
                Open landing page ↗
              </a>
            </>
          )}
        </div>

        {error && <p role="alert" className="mt-4 rounded-xl border border-red-400/40 bg-red-500/15 px-4 py-3 text-sm">{error}</p>}

        <section className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-5" aria-label="Key figures">
          <StatTile label="Participants" value={stats.total_users} />
          <StatTile label="Cards generated" value={stats.cards_generated} />
          <StatTile label="Cards scratched" value={stats.cards_scratched} note={`${percent(stats.cards_scratched, stats.cards_generated)} of generated`} />
          <StatTile label="Prizes won" value={stats.rewards_distributed} note={`${percent(stats.rewards_distributed, stats.cards_scratched)} of scratched`} />
          <StatTile label="Prizes redeemed" value={stats.rewards_redeemed} note={`${percent(stats.rewards_redeemed, stats.rewards_distributed)} of won`} />
        </section>

        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <RewardTable rows={overview.distribution} client={client} onChanged={load} />
          <RedeemBox client={client} onRedeemed={load} />
        </div>

        <ActivityTable rows={overview.recent_activity} />
      </div>
    </main>
  );
}
