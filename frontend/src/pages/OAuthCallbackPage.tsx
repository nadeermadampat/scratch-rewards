import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { PageMessage, Spinner } from "../components/ui";
import { clearOAuthSession, readOAuthSession } from "../lib/oauthSession";

/** Where the platform sends the browser back after sign-in (`/oauth/callback`). */
export function OAuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [failure, setFailure] = useState<string | null>(null);
  const [slug, setSlug] = useState<string | null>(null);
  const started = useRef(false); // the code is single-use: never send it twice

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const session = readOAuthSession();
    clearOAuthSession();
    setSlug(session?.slug ?? null);
    const state = params.get("state");
    const code = params.get("code");

    if (params.get("error")) {
      setFailure(
        params.get("error") === "access_denied"
          ? "You didn't allow access, so we couldn't confirm your subscription."
          : "Google sign-in was cancelled or failed.",
      );
      return;
    }
    if (!session || !state || !code || state !== session.state) {
      setFailure("This sign-in link doesn't match this browser. Please start again from the campaign page.");
      return;
    }

    (async () => {
      try {
        const verification = await api.completeOAuth(state, code);
        if (verification.status !== "verified" || !verification.verification_token) {
          setFailure(verification.message ?? "We couldn't confirm your subscription.");
          return;
        }
        const card = await api.issueCard(verification.verification_token);
        // Coming through the campaign always ends in scratching, even for a returning participant.
        navigate(`/s/${card.token}`, { replace: true, state: { replay: true } });
      } catch (e) {
        setFailure((e as ApiError).message);
      }
    })();
  }, [params, navigate]);

  if (failure) {
    return (
      <PageMessage icon="⚠️" title="We couldn't verify your subscription">
        <p>{failure}</p>
        <Link to={slug ? `/c/${slug}` : "/"} className="btn-primary">Try again</Link>
      </PageMessage>
    );
  }
  return (
    <PageMessage icon={<Spinner className="h-10 w-10" />} title="Confirming with YouTube…">
      <p>This takes a few seconds. Please keep this page open.</p>
    </PageMessage>
  );
}
