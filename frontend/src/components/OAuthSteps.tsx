import { motion } from "framer-motion";
import { useState } from "react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { Campaign } from "../api/types";
import { saveOAuthSession } from "../lib/oauthSession";
import { getDeviceId } from "../lib/util";
import { Step } from "./Step";
import { Spinner, YouTubeIcon } from "./ui";

function GoogleLogo() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 48 48" aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.5 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.2C12.4 13.7 17.7 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.1 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.4c-.5 2.9-2.2 5.3-4.6 7l7.6 5.9c4.4-4.1 6.7-10.1 6.7-17.4z" />
      <path fill="#FBBC05" d="M10.5 28.6c-.5-1.5-.8-3-.8-4.6s.3-3.200.8-4.600l-7.900-6.200C.9 16.500 0 20.100 0 24s.9 7.500 2.600 10.800l7.900-6.200z" />
      <path fill="#34A853" d="M24 48c6.500 0 11.900-2.100 15.900-5.800l-7.600-5.900c-2.100 1.400-4.800 2.300-8.300 2.300-6.300 0-11.600-4.200-13.500-9.900l-7.900 6.200C6.500 42.600 14.600 48 24 48z" />
    </svg>
  );
}

/**
 * Landing-page steps when the campaign verifies with Google sign-in.
 * With `auto_subscribe`, signing in also subscribes the account, so the page
 * says exactly that before the participant leaves for Google.
 */
export function OAuthSteps({ campaign }: { campaign: Campaign }) {
  const { platform, engagement } = campaign;
  const subscribes = platform.auto_subscribe;
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { authorization_url, state } = await api.authorize({
        campaign_id: campaign.id,
        device_id: getDeviceId(),
        name: name.trim() || undefined,
        email: email.trim() || undefined,
        consent,
      });
      saveOAuthSession({ state, slug: campaign.slug });
      window.location.assign(authorization_url);
    } catch (e) {
      setError((e as ApiError).message);
      setBusy(false);
    }
  };

  return (
    <motion.form
      onSubmit={onSubmit}
      className="panel mt-7 p-5"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15, duration: 0.4 }}
    >
      <ol className="space-y-6">
        {!subscribes && (
          <Step number={1} title={`${platform.action_label} to ${engagement.title} on ${platform.display_name}`}>
            <a
              href={engagement.url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn w-full text-white hover:brightness-110"
              style={{ backgroundColor: platform.brand_color }}
            >
              <YouTubeIcon /> {platform.action_label} on {platform.display_name}
            </a>
            <p className="mt-2 text-xs text-white/50">Opens {platform.display_name} in a new tab. Subscribe there, then come back here.</p>
          </Step>
        )}

        <Step number={subscribes ? 1 : 2} title="Tell us who you are (optional)">
          <div className="space-y-2.5">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-white/60">Name</span>
              <input className="field" value={name} onChange={(e) => setName(e.target.value)} maxLength={120} autoComplete="name" placeholder="Asha Menon" />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-white/60">Email</span>
              <input className="field" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" inputMode="email" placeholder="asha@example.com" />
            </label>
          </div>
        </Step>

        <Step
          number={subscribes ? 2 : 3}
          title={subscribes ? `${platform.action_label} to ${engagement.title} with Google` : "Confirm your subscription with Google"}
        >
          <div className="rounded-xl bg-white/[0.06] px-3.5 py-3 text-sm text-white/75">
            <p className="font-medium text-white">What happens when you continue</p>
            <ul className="mt-1.5 list-disc space-y-1 pl-5">
              <li>Google asks you to sign in and allow access to your {platform.display_name} account.</li>
              {subscribes ? (
                <li>
                  We <strong className="text-white">subscribe your account to {engagement.title}</strong> if it isn't
                  subscribed already. Nothing else is changed.
                </li>
              ) : (
                <li>We only check whether your account is subscribed to {engagement.title}.</li>
              )}
              <li>We give the access back to Google straight away and don't keep it.</li>
            </ul>
          </div>

          <label className="mt-4 flex cursor-pointer items-start gap-3 text-sm text-white/75">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-0.5 h-5 w-5 shrink-0 rounded accent-[rgb(var(--accent))]"
            />
            <span>
              I agree to the campaign terms{subscribes ? `, to being subscribed to ${engagement.title},` : ""} and to my
              details being stored to run this promotion.
            </span>
          </label>

          {error && (
            <p role="alert" className="mt-3 rounded-xl border border-red-400/40 bg-red-500/15 px-3.5 py-2.5 text-sm">
              {error}
            </p>
          )}

          <button type="submit" className="btn mt-4 w-full bg-white text-[#1f1f1f] hover:bg-white/90" disabled={busy || !consent}>
            {busy ? (<><Spinner /> Opening Google…</>) : (<><GoogleLogo /> Continue with Google</>)}
          </button>
          {!busy && !consent && <p className="mt-2 text-center text-xs text-white/45">Tick the box above to continue.</p>}
        </Step>
      </ol>
    </motion.form>
  );
}
