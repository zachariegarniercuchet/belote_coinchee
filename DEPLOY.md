# Deploying the Belote Coinchée backend to Render

## Short answer

Yes — this is a good fit for Render. The backend is a Flask + Flask-SocketIO
app that already reads `PORT` from the environment and binds `0.0.0.0`, which
is exactly what Render expects from a Web Service. No rewrite needed, only a
few small config changes (already made in this repo, see "What changed"
below) so that a frontend hosted elsewhere (like your GitHub Pages page) can
talk to it.

Render's free plan works, with one caveat: free services spin down after
~15 minutes of inactivity and take 30-60s to wake back up on the next
request. Fine for a "let's play Belote on Friday night" app; annoying if you
want it always instantly ready (in that case, use a paid instance, or a
tiny external cron/uptime pinger to keep it warm).

## Two ways to use it

**Option A — simplest: let Render serve the whole app (frontend + backend).**
Render's Flask app already serves `index.html`, `app.js`, `style.css`
itself. Once deployed, `https://your-app.onrender.com` is the whole game —
lobby, QR code, everything. You don't need GitHub Pages at all; you could
just link people to the Render URL directly, or make your GitHub Pages URL
redirect to it.

**Option B — keep the GitHub Pages URL as the front door, calling Render as
a pure backend.** Your existing page stays where it is, but it opens a
Socket.IO connection to the Render service instead of expecting a
same-origin server. This repo now includes a ready-to-copy static build for
that: see `frontend-github-pages/`.

Pick A if you just want it working with the least fuss. Pick B if you're
attached to the `zachariegarniercuchet.github.io/belote_choinchee/` URL.

---

## 1. Push this repo to GitHub

You said it's already on GitHub — make sure the changes in this delivery
(`extensions.py`, `server.py`, `app.js`, `render.yaml`, `DEPLOY.md`,
`frontend-github-pages/`) are committed and pushed.

## 2. Create the Render Web Service

1. Go to https://dashboard.render.com → **New** → **Web Service**.
2. Connect your GitHub account/repo and pick the `belote_coinchee` repo.
   - If `render.yaml` is at the repo root (it is), Render will detect it
     and offer to create the service from it directly ("Blueprint"). Easiest.
   - Otherwise, configure manually:
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python server.py`
     - **Plan**: Free (or Starter if you want no spin-down)
3. Environment variables (Render → your service → **Environment**):
   - `BELOTE_SECRET` — any random string (Flask session secret). Render can
     generate one for you if using `render.yaml`.
   - `CORS_ALLOWED_ORIGIN` — who's allowed to open a Socket.IO connection to
     this backend from a browser.
     - `*` (default) is fine to get started.
     - For real use, set it to your exact frontend origin, e.g.
       `https://zachariegarniercuchet.github.io` (no trailing slash, no
       path) — tighter and avoids random sites embedding your backend.
   - `PUBLIC_BASE_URL` — only needed if you want the in-app QR code / share
     link to point somewhere other than the Render URL itself (e.g. at your
     GitHub Pages URL). Example:
     `https://zachariegarniercuchet.github.io/belote_choinchee`
     Leave empty to have links point at the Render app itself (fine for
     Option A).
4. Click **Create Web Service** / **Apply**. Render will build and deploy;
   first deploy takes a couple of minutes. You'll get a URL like
   `https://belote-coinchee.onrender.com`.
5. Open that URL. You should see the lobby screen. Create a room, then open
   the same URL on your phone (any network, not just Wi-Fi now) and join
   with the code — this already proves the backend works standalone
   (Option A).

## 3. (Option B only) Point GitHub Pages at the Render backend

1. Copy the three files from `frontend-github-pages/` in this repo
   (`index.html`, `app.js`, `style.css`) into your GitHub Pages repo,
   replacing what's there.
2. In `index.html`, set the backend URL to your real Render URL:
   ```html
   <script>
     window.BELOTE_BACKEND_URL = "https://belote-coinchee.onrender.com";
   </script>
   ```
3. Commit and push. GitHub Pages will redeploy automatically.
4. If you set `PUBLIC_BASE_URL` on Render to your GitHub Pages URL (step 2
   above), the QR code / "copy link" shown in the lobby will now point back
   to your GitHub Pages page (with `?code=XXXX`), which pre-fills the join
   code — nice for scanning from a phone.

## What changed in the code (and why)

- **`extensions.py`** — `SocketIO(...)` now takes `cors_allowed_origins`
  from the `CORS_ALLOWED_ORIGIN` env var (default `*`). Without this,
  browsers block Socket.IO connections from a different origin (GitHub
  Pages → Render is cross-origin), so real-time updates would silently
  never arrive.
- **`app.js`** — `io()` (same-origin) is now `io(BACKEND_URL)` when
  `window.BELOTE_BACKEND_URL` is set, so the same script works whether it's
  served by Flask itself (Option A, leave unset) or served statically
  elsewhere (Option B, set it).
- **`server.py`** — the lobby/QR share-link used to be built from a
  best-guess *local Wi-Fi IP* (`get_lan_ip()`), which only makes sense when
  you and your friends are physically on the same router. On the internet
  that guess is meaningless, so it's now overridable with `PUBLIC_BASE_URL`;
  the link format also changed from `/join/<code>` to `/?code=<code>` (a
  query string works on both a Flask route and a plain static file, which
  a path segment doesn't on GitHub Pages).
- **`frontend-github-pages/`** — a ready-to-copy static build of the
  frontend (Jinja placeholders replaced with plain paths, plus the small
  script block described above) for Option B.

## Notes / gotchas

- **Free-tier cold start**: the first request after ~15 min idle can take
  30-60s while Render wakes the container. The lobby will just look like
  it's hanging — worth warning your friends, or upgrading to a paid
  instance if that's annoying.
- **In-memory state**: rooms and game state live in the Python process's
  memory (`RoomManager`, `GameSession`). A redeploy or a free-tier spin-down
  mid-game will lose that room's state — nobody will be logged out
  violently, but ongoing games won't survive a restart. Fine for a casual
  card game; would need a real datastore (Redis, etc.) if you ever needed
  persistence across restarts.
- **Single instance only**: don't scale this service to more than one
  instance/worker — room state lives in one process's memory, so a second
  instance would have no idea about rooms created on the first. Render's
  free/starter plans default to a single instance, so this is only a
  concern if you explicitly turn on scaling later.
- **WebSockets**: Render supports WebSocket connections on Web Services
  natively, no special configuration needed beyond what's already here.
