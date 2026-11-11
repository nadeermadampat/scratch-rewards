import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { CampaignSummary } from "../api/types";
import { PageMessage, Spinner } from "../components/ui";

/** Entry point: goes straight to the campaign when there is only one. */
export function HomePage() {
  const [campaigns, setCampaigns] = useState<CampaignSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listCampaigns().then(setCampaigns).catch((e: ApiError) => setError(e.message));
  }, []);

  if (error) {
    return (
      <PageMessage icon="⚠️" title="This page didn't load">
        <p>{error}</p>
        <button className="btn-primary" onClick={() => window.location.reload()}>Try again</button>
      </PageMessage>
    );
  }
  if (!campaigns) return <PageMessage icon={<Spinner className="h-10 w-10" />} title="Loading…" />;
  if (campaigns.length === 1) return <Navigate to={`/c/${campaigns[0].slug}`} replace />;
  if (campaigns.length === 0) {
    return <PageMessage icon="🎟️" title="No campaigns are running right now"><p>Please check back soon.</p></PageMessage>;
  }

  return (
    <main className="app-bg min-h-[100dvh] px-4 py-10">
      <div className="mx-auto max-w-md">
        <h1 className="text-center font-display text-3xl font-extrabold">Scratch &amp; Win</h1>
        <ul className="mt-6 space-y-3">
          {campaigns.map((campaign) => (
            <li key={campaign.id}>
              <Link to={`/c/${campaign.slug}`} className="panel block p-5 transition hover:bg-white/[0.1]">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">{campaign.client_name}</p>
                <p className="mt-1 font-display text-xl font-bold">{campaign.headline ?? campaign.name}</p>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}
