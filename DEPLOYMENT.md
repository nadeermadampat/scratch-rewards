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
4. Do **not** add the `YOUTUBE_*` variables unless you switch to OAuth verification. The
   channel is stored in the database by the seed step below.

`TRUST_FORWARDED_FOR=true` makes rate limiting and the audit trail use the visitor's IP
address instead of Vercel's proxy address.

---

## 6. Create the tables and the demo campaign

Migrations are run once from your machine against the hosted database.

1. Open PowerShell in `scratch-rewards\backend`.
2. Point this terminal at the hosted database (paste the string from section 4, keep the quotes):

   ```powershell
   $env:DATABASE_URL = "<paste connection string>"
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
- **Verification is still simulated.** Anyone who clicks through receives a card.
- `docker-compose.yml`, the `Dockerfile`s and `nginx.conf` are not used by Vercel.

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
