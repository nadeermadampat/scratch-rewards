# Deploying Scratch Rewards to Vercel

This guide deploys the stack as **two Vercel projects from one GitHub repository**, plus a
hosted PostgreSQL database:

| Piece | Vercel project | Root directory | What runs |
|---|---|---|---|
| API | `scratch-rewards-api` | `backend` | FastAPI as a Vercel Function (Python 3.12) |
| Web app | `scratch-rewards-web` | `frontend` | Vite build served as static files |
| Database | Postgres from the Vercel Marketplace (Neon in this guide) | – | PostgreSQL |

The web app calls the API on its own `*.vercel.app` address (cross-origin, allowed by CORS).

> **Status:** these steps follow the Vercel documentation as read on 11 Nov 2026, but this
> project has **not yet been deployed to Vercel or run against PostgreSQL**. Section 9 is
> the check that it works; section 11 lists what to look at if a step fails.

Commands are written for **Windows PowerShell**. Run each from the folder named in the step.

---

## 1. Before you start

1. Have these accounts: **GitHub** and **Vercel** (sign up at vercel.com with "Continue with GitHub").
2. Check the tools are installed:

   ```powershell
   git --version
   ```

   ```powershell
   node --version
   ```

   ```powershell
   py -3.12 --version
   ```

3. Confirm the app works locally first (see `README.md`, "Quick start").
4. Decide the two project names. This guide uses `scratch-rewards-api` and
   `scratch-rewards-web`. Vercel gives each a URL like `https://<name>.vercel.app`; if a
   name is taken it adds a suffix, so always copy the real URL from the dashboard.

Vercel's Hobby plan is for personal, non-commercial use. A client-facing campaign needs a Pro plan.

---

## 2. Put the code on GitHub

1. Open PowerShell in the project folder (`scratch-rewards`).
2. Confirm secrets are ignored. Both lines must be printed back:

   ```powershell
   git check-ignore .env backend/scratch_rewards.db
   ```

3. Commit:

   ```powershell
   git add .
   ```

   ```powershell
   git status
   ```

   Check that `.env` is **not** in the list, then:

   ```powershell
   git commit -m "Scratch Rewards MVP"
   ```

4. On github.com: **+** (top right) → **New repository** → name it `scratch-rewards` →
   **Private** → leave "Add a README" unticked → **Create repository**.
5. Copy the two commands GitHub shows under "…push an existing repository" and run them. They look like:

   ```powershell
   git remote add origin https://github.com/<your-user>/scratch-rewards.git
   ```

   ```powershell
   git push -u origin HEAD
   ```

6. Refresh the GitHub page and confirm you see `backend/`, `frontend/` and `README.md`, and no `.env`.

---

## 3. Create the API project

1. Go to vercel.com → **Add New…** → **Project**.
2. Under **Import Git Repository**, find `scratch-rewards` and click **Import**.
   If it is not listed, click **Adjust GitHub App Permissions** and grant access to the repository.
3. **Project Name:** `scratch-rewards-api`.
4. **Root Directory:** click **Edit**, select `backend`, click **Continue**.
5. **Framework Preset:** Vercel should detect **FastAPI**. It finds the app because
   `backend/app/main.py` exports a FastAPI instance named `app`, and installs
   `backend/requirements.txt`. Leave build and install settings at their defaults.
6. Do not add environment variables yet. Click **Deploy**.
7. This first deployment will build but **cannot work yet** (no database). That is expected.
8. Open the project → **Settings → Domains** and copy the production URL.
   Below it is written as `https://API_URL`.

---

## 4. Create the database

1. In the `scratch-rewards-api` project open the **Storage** tab.
2. Click **Create Database** (or **Browse Marketplace**) → choose **Neon** (Postgres) → **Continue**.
3. Accept the terms, pick the **region closest to your users**, pick the free plan, name it
   `scratch-rewards-db`, click **Create**.
4. When asked which project to connect, select **`scratch-rewards-api`**, keep all
   environments ticked, and confirm.
5. Open **Settings → Environment Variables** on the API project and look at what was added.
   The app reads **`DATABASE_URL`**.
   - If a variable named `DATABASE_URL` exists, nothing more to do here.
   - If the integration used other names (for example `POSTGRES_URL`), click **Add New**,
     name it `DATABASE_URL`, paste the same connection string as the value, tick
     **Production** and **Preview**, and **Save**.
6. Click the eye icon on the connection string and **copy it**. You need it in section 6.
   Treat it as a password.

The app accepts `postgres://…` and `postgresql://…` URLs and both pooled and direct connection strings.

---

## 5. Set the API environment variables

1. Generate two secrets locally. Run this twice and keep both outputs:

   ```powershell
   py -3.12 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. In the API project → **Settings → Environment Variables**, add each row below
   (**Add New** → Key, Value → tick **Production** → **Save**):

   | Key | Value |
   |---|---|
   | `ENVIRONMENT` | `production` |
   | `SECRET_KEY` | first generated secret |
   | `ADMIN_API_KEY` | second generated secret (this is the admin dashboard password) |
   | `TRUST_FORWARDED_FOR` | `true` |
   | `RATE_LIMIT_ENABLED` | `true` |
   | `APP_BASE_URL` | `https://placeholder.invalid` for now; fixed in section 8 |
   | `CORS_ORIGINS` | `https://placeholder.invalid` for now; fixed in section 8 |

3. Mark `SECRET_KEY`, `ADMIN_API_KEY` and `DATABASE_URL` as **Sensitive** if the option is shown.
4. Do **not** add the `YOUTUBE_*` variables yet. Real verification with Google sign-in is
   switched on later in section 13. The channel is stored in the database by the seed step below.

`TRUST_FORWARDED_FOR=true` makes rate limiting and the audit trail use the visitor's IP
address instead of Vercel's proxy address.

---

## 6. Create the tables and the demo campaign

Migrations are run once from your machine against the hosted database.

1. Open PowerShell in `scratch-rewards\backend`.
2. Point this terminal at the hosted database (paste the string from section 4, keep the quotes):

   ```powershell
   $env:DATABASE_URL = "postgresql://neondb_owner:npg_s3HryDuV8nLY@ep-wild-hill-azo639qg-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?channel_binding=require&sslmode=require"
   ```

3. Create the tables:

   ```powershell
   .venv\Scripts\python -m alembic upgrade head
   ```

   Expected last line: `Running upgrade  -> 0001, Initial schema…`

4. Load the campaign and rewards from `config/app_config.yaml`. The YouTube channel comes
   from `YOUTUBE_CHANNEL_*` in your local `.env`:

   ```powershell
   .venv\Scripts\python -m app.seed
   ```

   Add `--demo-activity` only if you want 36 fake participants in the dashboard.

5. Remove the variable so later local commands use SQLite again:

   ```powershell
   Remove-Item Env:DATABASE_URL
   ```

To change the channel later: edit `.env`, repeat steps 2, 4 and 5. Existing cards are not touched.
For every future schema change, repeat steps 2, 3 and 5 **before** deploying the new code.

---

## 7. Redeploy the API and check it

1. API project → **Deployments** → **⋯** on the latest deployment → **Redeploy** → **Redeploy**.
   Environment variables only apply to deployments made after they were saved.
2. When it shows **Ready**, open these in a browser:

   | URL | Expected |
   |---|---|
   | `https://API_URL/api/health` | `{"success":true,"data":{"status":"ok"}}` |
   | `https://API_URL/api/campaigns` | a list containing your campaign |
   | `https://API_URL/api/social-platforms` | `youtube` with `"enabled":true` |
   | `https://API_URL/api/docs` | the interactive API documentation |

   If `youtube` shows `"enabled":false`, `config/app_config.yaml` was not bundled with the
   function. See section 11.

---

## 8. Create the web project and connect the two

1. vercel.com → **Add New…** → **Project** → **Import** the same `scratch-rewards` repository again.
2. **Project Name:** `scratch-rewards-web`.
3. **Root Directory:** **Edit** → select `frontend` → **Continue**.
4. **Framework Preset:** **Vite**. Build command `npm run build` and output directory `dist`
   should be filled in; leave them.
5. Open **Environment Variables** on this screen and add:

   | Key | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://API_URL/api` (your real API URL, ending in `/api`, no trailing slash) |

6. Click **Deploy**. When it is ready, copy the production URL from **Settings → Domains**.
   Below it is written as `https://WEB_URL`.
7. Go back to the **API** project → **Settings → Environment Variables** and edit:

   | Key | New value |
   |---|---|
   | `APP_BASE_URL` | `https://WEB_URL` |
   | `CORS_ORIGINS` | `https://WEB_URL` |

   No trailing slash on either. `APP_BASE_URL` is what scratch card links are built from.
8. Redeploy the **API** again (section 7, step 1).

`VITE_API_BASE_URL` is baked into the web app at build time. If the API URL ever changes,
update the variable and redeploy the **web** project.

`frontend/vercel.json` already contains the rewrite that makes `/c/…`, `/s/…` and `/admin`
load on refresh, and sets `Referrer-Policy: no-referrer` so card links are not leaked.

---

## 9. Test the live site

Do this on a phone as well as a desktop.

1. Open `https://WEB_URL`. The campaign landing page appears with your channel name.
2. Tap **Subscribe on YouTube**; YouTube opens in a new tab on your channel. Return to the page.
3. Tick the consent box → **I've subscribed — verify** → **Open my scratch card**.
4. Check the card address starts with `https://WEB_URL/s/`.
5. Scratch with a finger. The reward shows through, the coating clears at about half, and a claim reference appears.
6. Refresh the page: the same result and claim reference are shown, with no coating.
7. Go back to the landing page and verify again: you get "You already have a scratch card".
8. Open `https://WEB_URL/admin`, enter the `ADMIN_API_KEY` value, and confirm the new card
   is at the top of **Recent activity**.
9. Open a card link with a few characters changed: "We can't find this scratch card".

---

## 10. Everyday operations

- **Deploy a change:** `git push`. Both projects rebuild from the `main` branch automatically.
- **Roll back:** project → **Deployments** → **⋯** on an earlier deployment → **Promote to Production** (or **Instant Rollback**).
- **Logs:** project → **Logs**. Every request line carries a request id; card tokens are shortened.
- **Custom domain:** web project → **Settings → Domains** → **Add** → follow the DNS instructions.
  Then set `APP_BASE_URL` and `CORS_ORIGINS` on the API to the new address and redeploy the API.
- **Pause a campaign:** admin dashboard → **Pause campaign**. No deployment needed.
- **Preview deployments** (from branches and pull requests) get their own URLs. The web
  preview will be blocked by CORS unless you add its URL to `CORS_ORIGINS`
  (comma-separated) for the Preview environment.

---

## 11. If something fails

| Symptom | Likely cause and fix |
|---|---|
| API build fails because it cannot find the FastAPI app, or builds the wrong thing | Root Directory is not `backend`. Fix it in **Settings → General → Root Directory** and redeploy. |
| `/api/health` works but `/api/campaigns` returns `INTERNAL_ERROR` | `DATABASE_URL` is missing or wrong on the API project, or section 6 was skipped. Check **Logs** for the database error. |
| `/api/campaigns` returns an empty list | The seed step (section 6, step 4) was not run against the hosted database. |
| `/api/social-platforms` shows `youtube` as `"enabled":false` | `config/app_config.yaml` is not in the function bundle. Vercel's docs say Python functions include all project files reachable at build time, so this should not happen; if it does, add an `includeFiles` entry for `config/**` under `functions` → `app/main.py` in a `backend/vercel.json` (check the exact syntax in Vercel's function configuration docs), commit and push. |
| Web page shows "Can't reach the server" | `VITE_API_BASE_URL` is wrong or the web project was not redeployed after setting it; or `CORS_ORIGINS` on the API does not exactly match the web address (scheme, host, no trailing slash). The browser console shows which. |
| Refreshing `/s/…` or `/admin` gives a Vercel 404 | Root Directory of the web project is not `frontend`, so `frontend/vercel.json` is not being used. |
| Scratch card links point at `placeholder.invalid` or `localhost` | `APP_BASE_URL` on the API was not updated, or the API was not redeployed afterwards. |
| Admin page says the admin API is disabled | `ADMIN_API_KEY` is not set on the API project for Production. |
| Database errors mentioning prepared statements or too many connections | Use the **pooled** connection string from the database provider as `DATABASE_URL`. |

---

## 12. What changes on Vercel compared with local or Docker

- **Rate limiting is weaker.** The limiter keeps its counters in memory, and Vercel runs
  several short-lived instances, each with its own counters. Move it to Redis (Upstash is in
  the Vercel Marketplace) before a real campaign.
- **No local files.** SQLite cannot be used; the database must be hosted PostgreSQL.
- **Migrations are manual** (section 6). Nothing runs them on deploy.
- **Verification is simulated until you complete section 13.** In simulated mode anyone who clicks through receives a card.
- `docker-compose.yml`, the `Dockerfile`s and `nginx.conf` are not used by Vercel.

---

## 13. Turn on real verification (Google sign-in and one-click subscribe)

By default the site runs in **simulated** mode. These steps switch it to Google sign-in:
the visitor signs in, the server checks with YouTube whether that account is subscribed to
your channel, and (with one-click subscribe on) subscribes it if it is not. No database
migration is needed.

> **Status:** this flow passes its automated tests against a stand-in for Google, but has
> **not been run against the real Google and YouTube services**. Do step 13.5 before
> sending real visitors to it. Menu names in Google Cloud Console change from time to
> time; look for the nearest match if a label differs.

### 13.1 Create the Google Cloud project

1. Open <https://console.cloud.google.com> and sign in with the Google account that should own the app.
2. Project picker (top bar) → **New Project** → name it `scratch-rewards` → **Create**, then select it.
3. Menu → **APIs & Services → Library** → search **YouTube Data API v3** → open it → **Enable**.

### 13.2 Configure the consent screen

1. Menu → **APIs & Services → OAuth consent screen** (also shown as **Google Auth Platform**).
2. **Get started** / **Branding**: app name (what visitors see, e.g. your brand name), a support email, then **Audience: External**, a developer contact email, agree, **Create**.
3. **Data Access** (or **Scopes**) → **Add or remove scopes** → tick one of the following, then **Update** and **Save**:

   | Mode | Scope to add |
   |---|---|
   | One-click subscribe (default) | `https://www.googleapis.com/auth/youtube.force-ssl` |
   | Check only | `https://www.googleapis.com/auth/youtube.readonly` |

4. **Audience** → **Test users** → **Add users** → add the Google email of everyone who will
   test. While the app is in **Testing**, only these accounts (up to 100) can sign in.

### 13.3 Create the OAuth client

1. **APIs & Services → Credentials** (or **Clients**) → **Create credentials → OAuth client ID**.
2. **Application type:** Web application. **Name:** `scratch-rewards-web`.
3. **Authorized redirect URIs** → **Add URI**, once for each address the site is served from:

   - `https://WEB_URL/oauth/callback` (your real web address, exactly as in the browser bar, no trailing slash)
   - `http://localhost:5173/oauth/callback` (only if you want to test locally)

4. **Create**. Copy the **Client ID** and **Client secret**. Treat the secret as a password.

The redirect address is built from `APP_BASE_URL` on the API project, so that variable must
be exactly `https://WEB_URL`. A mismatch gives Google's `redirect_uri_mismatch` error.

### 13.4 Set the variables and redeploy

1. Push the latest code so both Vercel projects rebuild:

   ```powershell
   git add .
   ```

   ```powershell
   git commit -m "Google sign-in verification"
   ```

   ```powershell
   git push
   ```

2. **API** project → **Settings → Environment Variables** → add for **Production**:

   | Key | Value |
   |---|---|
   | `YOUTUBE_VERIFICATION_MODE` | `oauth` |
   | `YOUTUBE_AUTO_SUBSCRIBE` | `true` for one-click subscribe, `false` for check only |
   | `YOUTUBE_OAUTH_CLIENT_ID` | the Client ID |
   | `YOUTUBE_OAUTH_CLIENT_SECRET` | the Client secret (mark as Sensitive) |

3. Redeploy the **API** project (**Deployments → ⋯ → Redeploy**) so the variables apply.
4. Check `https://API_URL/api/campaigns/<campaign-slug>`: `platform.verification_mode`
   should be `"oauth"`.

The channel does not need changing: a handle such as `@KodeKloud` is looked up automatically.
To switch back to simulated mode, delete `YOUTUBE_VERIFICATION_MODE` and redeploy the API.

### 13.5 Test with a real account

Use a Google account that is in the test-user list and is **not** yet subscribed to the channel.

1. Open `https://WEB_URL`. The form now ends with **Continue with Google**.
2. Tick the consent box → **Continue with Google** → pick the account. Google shows an
   "unverified app" notice while in Testing: **Continue**. Allow the YouTube permission.
3. You return to the site, see "Confirming with YouTube…", then land on your scratch card.
4. Open YouTube with the same account → **Subscriptions**: the channel is now listed.
5. Repeat from another browser with the **same** Google account: you get the same card, not a new one.
6. Repeat and press **Cancel** on Google's screen: the site says access was not allowed and offers **Try again**.
7. Admin dashboard → the new card appears in **Recent activity**.

If step 3 fails, the message on the page says why; the API project's **Logs** has the detail
(`YouTube API error: <status> <reason>`).

### 13.6 Before opening it to the public

- **Google verification.** In **Audience**, **Publish app** moves it out of Testing. Because
  the YouTube scopes are sensitive, Google then requires verification: a privacy policy on
  your own verified domain, a justification for the scope and usually a short demo video.
  Until that is approved, non-test users see a warning or are blocked.
- **Quota.** The YouTube Data API allows 10,000 units a day by default. A subscribe call is
  listed at about 50 units, so one-click subscribe supports roughly 190 new subscribers a
  day; check-only costs 2–3 units per visitor. Request a higher quota in
  **APIs & Services → YouTube Data API v3 → Quotas** before a campaign.
- **Policy.** Rewarding subscriptions, and subscribing accounts through the API in exchange
  for a prize, may conflict with YouTube's fake-engagement and API policies. Have this
  reviewed before applying for verification.
- **Privacy notice.** State that the site uses Google sign-in to check or create a YouTube
  subscription, stores the visitor's YouTube channel ID to prevent duplicate entries, and
  does not keep access to the account (the token is revoked immediately after use).

---

## Appendix: deploying with the Vercel CLI instead of the dashboard

Use this only if you prefer the terminal; the result is the same two projects.

```powershell
npm i -g vercel
```

```powershell
vercel login
```

From `scratch-rewards\backend`, create and deploy the API project (answer the prompts: new project, name `scratch-rewards-api`, directory `./`):

```powershell
vercel deploy --prod
```

Add each variable from section 5 (you are prompted for the value):

```powershell
vercel env add ADMIN_API_KEY --environment production
```

From `scratch-rewards\frontend`, do the same for the web project (`scratch-rewards-web`), add `VITE_API_BASE_URL`, then:

```powershell
vercel deploy --prod
```

The database (section 4) and the migration and seed steps (section 6) are the same.
CLI deployments are not connected to GitHub, so later changes need `vercel deploy --prod` again.
