# Scratch Rewards

A social media engagement platform: a business asks visitors to subscribe to its
YouTube channel, and each verified visitor gets a unique digital scratch card with a
prize decided on the server.

This is an MVP. Subscription verification is **simulated** and rewards are demo data,
but the structure is multi-client, multi-campaign and multi-platform from the start.

## What is implemented

- **Landing page** (`/c/<campaign-slug>`): client branding, prize teaser, subscribe button, optional name/email, consent, verify.
- **Scratch card** (`/s/<token>`): canvas foil coating, touch and mouse scratching, foil flakes, synthesised sound with a mute button, auto-reveal at a configurable threshold, confetti, and a "reveal without scratching" option for accessibility.
- **Result view** (same URL once completed): reward, claim reference, redemption instructions. Refreshing shows the same result.
- **Admin dashboard** (`/admin`): totals, reward odds versus actual distribution, recent activity, edit reward weights, enable/disable rewards, pause/resume a campaign, mark a reward as redeemed.
- **Backend**: REST API, weighted reward allocation with a CSPRNG, optional stock caps, card expiry, idempotent completion, rate limiting, audit trail, Alembic migration, seed data.

## Quick start (local, SQLite)

Requires Python 3.12 and Node 18.12 or newer.

```bash
cp .env.example .env        # then set SECRET_KEY and ADMIN_API_KEY
```

Backend (from `backend/`; on Windows use `py -3.12` if `python` is not CPython 3.12):

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m app.seed --demo-activity
.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

Frontend (from `frontend/`):

```bash
npm install
npm run dev
```

Open <http://localhost:5173>. The admin dashboard is at <http://localhost:5173/admin>
and asks for the `ADMIN_API_KEY` from `.env`. Interactive API docs are at
<http://localhost:8000/api/docs>.

To try it on a phone on the same network, open the "Network" URL that Vite prints and
set `APP_BASE_URL` and `CORS_ORIGINS` in `.env` to that address so generated card links point to it.

## Docker (PostgreSQL)

```bash
cp .env.example .env        # set SECRET_KEY, ADMIN_API_KEY, POSTGRES_PASSWORD
docker compose up --build
```

Open <http://localhost:8080>. The backend container runs migrations and seeds the demo
campaign on start. Set `PUBLIC_BASE_URL` when serving from another host name.

For a step-by-step Vercel deployment (two projects plus hosted Postgres), see
[DEPLOYMENT.md](DEPLOYMENT.md).

The images are plain containers with no cloud-specific services, so they can run on AWS
(ECS/Fargate + RDS) or Azure (Container Apps + Database for PostgreSQL) unchanged. Put
TLS in front, and replace the in-memory rate limiter before running more than one API
process (see Known limitations).

## Configuration

Secrets go in `.env`; everything else is in `backend/config/app_config.yaml`.

| Variable | Purpose |
|---|---|
| `ENVIRONMENT`, `LOG_LEVEL` | Runtime label and log verbosity |
| `APP_BASE_URL` | Public frontend URL, used to build scratch card links |
| `CORS_ORIGINS` | Comma-separated origins allowed to call the API |
| `SECRET_KEY` | Salt for hashed IP addresses in the audit trail |
| `ADMIN_API_KEY` | Key for the admin API (`X-Admin-Key` header). Admin is disabled when empty |
| `RATE_LIMIT_ENABLED` | Turn rate limiting on or off |
| `DATABASE_URL` | SQLAlchemy URL. SQLite by default; `postgresql+psycopg://…` for PostgreSQL |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Used by docker-compose |
| `PUBLIC_BASE_URL` | docker-compose only: public URL of the stack (default `http://localhost:8080`) |
| `YOUTUBE_CHANNEL_ID`, `YOUTUBE_CHANNEL_URL`, `YOUTUBE_CHANNEL_NAME` | Channel used when seeding the demo campaign |
| `YOUTUBE_API_KEY`, `YOUTUBE_OAUTH_CLIENT_ID`, `YOUTUBE_OAUTH_CLIENT_SECRET` | Only for `oauth` verification mode |

`app_config.yaml` holds card expiry (72 h), reveal threshold (50%), cards per
participant (1), verification token lifetime, rate limits, which providers are enabled
and in which mode, and the seed campaign and rewards. A campaign can override the three
scratch-card settings in its `settings` column.

## Architecture

```
frontend (React, Vite)                 backend (FastAPI)
  pages/        screens                  api/routes/   HTTP only: validation, envelopes
  hooks/        flow state machines      services/     business rules and transactions
  components/   ScratchCard, Confetti…   providers/    one adapter per social platform
  lib/scratch/  canvas engine            models/       SQLAlchemy tables
  api/          typed client             core/         config, security, rate limit, errors
```

The frontend never decides anything. It reports gestures; the API owns card state and the reward.

### Card lifecycle

| Step | Call | Card status | What the client learns |
|---|---|---|---|
| Verify subscription | `POST /api/subscriptions/verify` | – | One-time verification token (15 min) |
| Issue card | `POST /api/scratch-cards` | `issued` | Card token and URL. **The reward is chosen and stored here** |
| Open the link | `GET /api/scratch-cards/{token}` | `opened` | Branding, expiry, threshold. No reward |
| First scratch | `POST /api/scratch-cards/{token}/start` | `scratching` | The reward, so it can show through the coating |
| Threshold reached | `POST /api/scratch-cards/{token}/complete` | `completed` | Claim reference |

The reward has to reach the browser before the coating is gone, otherwise nothing could
show through while scratching. It is therefore released by `/start`, which is a recorded
state change, and never by a plain `GET` on an untouched card. Seeing it early gains
nothing: the reward cannot change, and the claim reference only exists after `/complete`.

`/complete` is a compare-and-set update, so two simultaneous requests cannot both
complete a card. Repeats return the same result with `already_completed: true` and are
logged as `card.duplicate_completion`.

### Social media providers

`providers/base.py` defines `SocialMediaProvider`:

- `info()` – display name, action label ("Subscribe"), colour, availability, verification mode
- `get_engagement_target(platform_config)` – the URL to send the user to
- `start_verification(...)` – an authorization URL when a redirect step is needed
- `verify(request)` – returns verified / failed, the method used, and a platform user id when known

`YouTubeProvider` implements it. Instagram, Facebook and TikTok are registered as
unavailable placeholders. To add a platform: write a subclass in its own module, list it
in `PROVIDER_CLASSES` in `providers/registry.py`, enable it in `app_config.yaml`, and
create campaigns with that `platform` and its own `platform_config`. No service, route
or table changes are needed.

### YouTube verification: what is and is not possible

- A redirect or a click on Subscribe proves nothing; YouTube sends no callback.
- Real verification means the user signs in with Google and grants `youtube.readonly`, then the server calls `subscriptions.list?mine=true&forChannelId=<channel>`. That scope is classed as sensitive, so Google requires app verification before public use.
- Without the user's OAuth grant you can only see subscriptions that the user has made public, which is not the default.
- There are no subscriber webhooks. A user can unsubscribe straight after winning; re-checking later needs a stored refresh token.
- `providers.youtube.verification_mode: oauth` selects a code path that implements the above. It has **not** been run against Google, and the frontend redirect and callback are not built.
- Rewarding people for subscribing may conflict with YouTube's fake-engagement and contest policies. Get this reviewed before a real launch.

## Database schema

| Table | Key columns |
|---|---|
| `clients` | `id`, `name`, `slug`, `tagline`, `logo_url`, `brand` (JSON colours) |
| `campaigns` | `id`, `client_id`, `name`, `slug`, `headline`, `description`, `terms`, `platform`, `platform_config` (JSON), `settings` (JSON), `starts_at`, `ends_at`, `status` |
| `users` | `id`, `anonymous_id` (per-browser), `name`, `email`, `phone`, `platform`, `platform_user_id`, `consent_at`, `created_at` |
| `rewards` | `id`, `campaign_id`, `name`, `description`, `reward_type`, `value`, `icon`, `weight`, `is_prize`, `total_quantity`, `issued_count`, `redemption_instructions`, `is_active` |
| `subscription_verifications` | `id`, `campaign_id`, `user_id`, `platform`, `status`, `method`, `token` (one-time), `expires_at`, `verified_at`, `consumed_at` |
| `scratch_cards` | `id`, `token` (unique), `user_id`, `campaign_id`, `reward_id`, `verification_id` (unique), `status`, `claim_reference` (unique), `redemption_status`, `generated_at`, `first_accessed_at`, `scratch_started_at`, `scratch_completed_at`, `redeemed_at`, `expires_at` |
| `audit_events` | `id`, `event_type`, `campaign_id`, `user_id`, `scratch_card_id`, `ip_hash`, `user_agent`, `payload`, `created_at` |

A scratch card row is also the record of who was given which reward and whether it was
redeemed. Migrations live in `backend/alembic/versions`.

## API

Every response is `{"success": true, "data": …}` or
`{"success": false, "error": {"code", "message", "details"}}`.

| Method and path | Purpose |
|---|---|
| `GET /api/campaigns` | Campaigns that are open now |
| `GET /api/campaigns/{id-or-slug}` | Campaign, branding, engagement target, prize names |
| `GET /api/social-platforms` | Known platforms and availability |
| `POST /api/subscriptions/verify` | Body: `campaign_id`, `consent`, `proof`, optional `device_id`, `name`, `email`, `phone` |
| `POST /api/scratch-cards` | Body: `verification_token`. Returns the card token and URL |
| `GET /api/scratch-cards/{token}` | Card state |
| `POST /api/scratch-cards/{token}/start` | Record the first scratch; returns the reward |
| `POST /api/scratch-cards/{token}/complete` | Complete the card; returns the claim reference |
| `GET /api/rewards/{id}` | Reward definition, without odds |
| `GET /api/admin/overview?campaign_id=` | Totals, distribution, recent activity |
| `GET /api/admin/campaigns`, `PATCH /api/admin/campaigns/{id}` | List campaigns; change name or status |
| `GET` / `POST /api/admin/campaigns/{id}/rewards`, `PATCH /api/admin/rewards/{id}` | List, add and edit rewards |
| `POST /api/admin/redemptions` | Body: `claim_reference`. Mark a reward redeemed |
| `GET /api/health` | Liveness |

Admin routes need the `X-Admin-Key` header. Common error codes: `VALIDATION_ERROR` (422),
`CONSENT_REQUIRED` (422), `CAMPAIGN_NOT_ACTIVE` (409), `VERIFICATION_INVALID` (403),
`VERIFICATION_EXPIRED` (410), `CARD_NOT_FOUND` (404), `CARD_EXPIRED` (410),
`NO_REWARDS_AVAILABLE` (409), `RATE_LIMITED` (429, with `Retry-After`).

## Security and privacy

- Card and verification tokens are 256-bit values from `secrets.token_urlsafe`. Malformed and unknown tokens get the same 404.
- Rewards are drawn with `secrets.SystemRandom` when the card is issued and never change. Editing weights affects future cards only.
- One card per verification (unique constraint) and, by default, one per participant per campaign. A repeat request returns the existing card.
- Tokens are kept out of access logs, and pages send no referrer.
- Name, email and phone are optional. IP addresses are stored only as a keyed hash. Consent is required and timestamped.
- The audit trail records verification results, card issue, open, start, completion, duplicate completion, expiry, redemption and admin changes.

## Tests

```bash
cd backend && .venv/Scripts/python -m pytest      # 35 tests
cd frontend && npm test                           # 6 tests
```

Backend tests cover token and claim-reference generation, weighted allocation
(distribution, zero weights, stock caps, exhaustion), and the API: the full journey,
reward hidden until scratched and unchanged across refreshes, duplicate completion,
verification replay, one card per participant, expired cards, invalid tokens, paused
campaigns, consent, validation, rate limiting and the admin endpoints. Frontend tests
cover the scratch-progress grid.

## Known limitations

- **Verification is simulated.** Anyone who clicks through gets a card.
- **Participant identity is a browser id.** Clearing storage or using another browser yields another card. Real identity needs OAuth or a verified email or phone.
- **Rate limiting is in memory**, so it is per process and resets on restart. Use Redis before scaling out.
- **Admin access is a single shared key** with no users or roles.
- **Card tokens are stored in plain text** so the admin and repeat requests can return the link. Hash them if that is not needed.
- Scratch progress is not saved between page loads; a refresh mid-scratch restores the coating (the reward is unchanged).
- The Docker images and the PostgreSQL path have not been run yet; only SQLite has been exercised.
- The scratch card has been driven with a mouse in a desktop browser at phone size, not on physical Android or iOS devices.

## Suggested next steps

1. Google OAuth flow for real YouTube verification, after the policy review above.
2. Test on real Android and iOS devices; add a QR code on the "card ready" screen for desktop-to-phone hand-off.
3. Admin users and roles, campaign and client creation in the UI, CSV export.
4. Redis-backed rate limiting, and abuse signals built from `audit_events` (many cards per IP hash, rapid completions).
5. Send the card link by email or SMS so a winner can recover it.
