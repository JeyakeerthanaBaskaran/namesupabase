# Streamlit + Supabase Demo (with Auth + Row Level Security)

A todo app where each user signs in and can only see and change **their own**
todos. Data lives in Supabase Postgres; access is enforced by the database,
not by the app.

## The key question: "my key is visible to everyone — is that a problem?"

Supabase gives you two kinds of API keys (Dashboard -> **Project Settings -> API Keys**):

| Key | Looks like | Public? | What it can do |
|---|---|---|---|
| **Publishable** (legacy name: `anon`) | `sb_publishable_...` | **Yes, safe to expose** | Only what your RLS policies allow |
| **Secret** (legacy name: `service_role`) | `sb_secret_...` | **Never** | Bypasses RLS — full access to everything |

The publishable key is *meant* to be seen. It just tells Supabase which
project you're talking to. **Row Level Security (RLS) policies are the real
lock.** The old version of this demo had a policy that said "anyone with the
publishable key can do anything", which is why it wasn't safe. Now:

- Signed-out requests get **nothing** (no table privileges, no policies).
- Signed-in users can only select/insert/update/delete rows where
  `user_id = their own id`.
- `user_id` is set by the database from the user's login token, so it can't
  be faked.

So even if someone copies your URL + publishable key and calls the API
directly, they only see their own (empty) data after signing up.

## How the pieces connect

```
Browser ──> Streamlit app (app.py, runs on a server)
               │  publishable key + the user's access token (JWT)
               ▼
            Supabase
              ├─ Auth: checks email/password, issues the JWT
              └─ Postgres: RLS reads auth.uid() from the JWT
                           and filters every query to that user's rows
```

Each browser session gets its own Supabase client (`st.session_state`), so
one user's login is never shared with another visitor.

---

## Step 1 — Create the table and security policies

1. Open your project at [supabase.com/dashboard](https://supabase.com/dashboard).
2. Left sidebar -> **SQL Editor** -> **New query**.
3. Paste the full contents of [`supabase/schema.sql`](supabase/schema.sql) and click **Run**.
   You should see "Success. No rows returned".
4. Check it: **Table Editor -> todos**. You should see the columns
   `id, task, is_complete, inserted_at, user_id`, with RLS shown as **enabled**.
   **Authentication -> Policies** should list four policies on `todos`.

## Step 2 — Configure Auth

1. **Authentication -> Sign In / Providers** -> make sure **Email** is enabled.
2. **Email confirmation** (same page, "Confirm email"):
   - **On** (default, recommended for real apps): new users get an email
     and must click the link before they can sign in.
   - **Off** (handy while testing locally): sign-up signs you in immediately.
3. If confirmation is on: **Authentication -> URL Configuration** -> set
   **Site URL** to where your app runs (`http://localhost:8501` locally, or
   your Streamlit Cloud URL later). The confirmation link redirects there.

> The built-in email sender is rate-limited (a few emails per hour) and meant
> for testing. For real users, configure custom SMTP under
> **Authentication -> Emails -> SMTP Settings**.

## Step 3 — Put the URL and key in secrets

1. Dashboard -> **Project Settings -> API Keys** -> copy the **Publishable key**.
   Dashboard -> **Project Settings -> Data API** (or the **Connect** button)
   -> copy the **Project URL**.
2. Create `.streamlit/secrets.toml` (copy from
   [`secrets.toml.example`](.streamlit/secrets.toml.example)):

   ```toml
   [connections.supabase_connection]
   url = "https://YOUR-PROJECT-REF.supabase.co"
   key = "sb_publishable_..."
   ```

3. **Never** put the secret key (`sb_secret_...`) in this app.
   `secrets.toml` is in `.gitignore`. Keep it that way.

## Step 4 — Run it locally

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`, then:

1. **Create account** tab -> enter an email + password (6+ chars).
2. Confirm the email if confirmation is on, then **Sign in**.
3. Add a few todos. In the dashboard, **Table Editor -> todos** shows the
   rows with your `user_id` filled in. Your user is listed under
   **Authentication -> Users**.

## Step 5 — Prove the security works

- **Two users:** open a private/incognito window, sign up with a second
  email. That user sees an empty list, never the first user's todos.
- **Raw API with only the public key** (PowerShell):

  ```powershell
  curl.exe "https://YOUR-PROJECT-REF.supabase.co/rest/v1/todos?select=*" -H "apikey: sb_publishable_..."
  ```

  You get a `permission denied` error. Signed-out access is blocked even
  though the key is "public".

## Step 6 — Deploy to Streamlit Community Cloud

1. Push to GitHub. Confirm `.streamlit/secrets.toml` is **not** in the repo
   (`git status` should not list it).
2. [share.streamlit.io](https://share.streamlit.io) -> **New app** -> pick the repo and `app.py`.
3. **Advanced settings -> Secrets** -> paste the same
   `[connections.supabase_connection]` block.
4. Deploy, then go back to Supabase **Authentication -> URL Configuration**
   and set **Site URL** to your `https://<app>.streamlit.app` address.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Could not find the table 'public.todos'` | Run `schema.sql` (Step 1). |
| `Email not confirmed` | Click the link in the confirmation email, or turn confirmation off (Step 2). |
| `Invalid login credentials` | Wrong email/password, or the account doesn't exist yet. |
| `email rate limit exceeded` | Built-in mailer limit. Wait, turn confirmation off for testing, or set up SMTP. |
| `new row violates row-level security policy` | You're not signed in, or tried to insert a `user_id` that isn't yours. |
| `SSL: CERTIFICATE_VERIFY_FAILED` | Antivirus/proxy is intercepting HTTPS. Run `pip install pip-system-certs` so Python trusts the Windows certificate store. |

## If a secret key ever leaks

Publishable key exposure is fine. If a **secret** key leaks (committed to
GitHub, pasted in chat, etc.): **Project Settings -> API Keys** -> delete
that secret key and create a new one immediately.
