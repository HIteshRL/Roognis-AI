# Roognis AI — Cloud Deploy for the Investor Demo

Single-VM, full-feature (AI tutor + quizzes + classes + teacher/parent
dashboards + **generated images + generated video + curriculum-grounded RAG**),
served over HTTPS. No GPU required — video and images run on Fal's hosted API.

**Target: live and rehearsed before July 22.** Aim to have this deployed and
smoke-tested by **July 18** to leave a buffer.

---

## 0. What you need (procure first)

| Item | Where | Notes |
|---|---|---|
| **Groq API key** | console.groq.com | ✅ you have this — powers the tutor |
| **Fal API key** | fal.ai → dashboard → keys | **Required for full scope** — powers BOTH image *and* video generation. Pay-as-you-go, a few dollars covers the demo. |
| **A cloud VM** | Hetzner / DigitalOcean / AWS Lightsail | Ubuntu 22.04, **4 vCPU / 8 GB RAM / 80 GB disk**. Hetzner CPX31 (~€15/mo) or DigitalOcean 8 GB (~$48/mo). 8 GB matters — Qdrant + embeddings + the Next.js build need headroom. |
| **A hostname** | your registrar, or free | A real domain (`demo.roognis.ai`, an A-record to the VM IP) looks best to investors. No domain? Use `<dashed-ip>.sslip.io` (e.g. `203-0-113-5.sslip.io`) — it resolves to your IP and still gets a real HTTPS cert. |

You do **not** need: a GPU, a Clerk account, a managed database, or Kubernetes.

---

## 1. Create the VM

Any provider works; the stack is plain Docker. Example (DigitalOcean):

1. Create a Droplet → Ubuntu 22.04 → **8 GB / 4 vCPU** → add your SSH key.
2. Note the public IP (e.g. `203.0.113.5`).
3. If using a real domain, add a DNS **A record**: `demo.yourdomain.com → 203.0.113.5`.
   (Skip this if using sslip.io.)
4. Open firewall ports **80** and **443** (and 22 for SSH).

---

## 2. Install Docker on the VM

```bash
ssh root@203.0.113.5
curl -fsSL https://get.docker.com | sh
docker --version && docker compose version
```

---

## 3. Get the code + configure

```bash
git clone https://github.com/HIteshRL/Roognis-AI.git
cd Roognis-AI
git checkout feat/multi-chat-cag         # until merged to master

cp .env.production.example .env
nano .env
```

Fill in `.env` (see [.env.production.example](../.env.production.example)):

```dotenv
DOMAIN=demo.yourdomain.com                 # or 203-0-113-5.sslip.io
PUBLIC_URL=https://demo.yourdomain.com     # must be https://$DOMAIN
API_SECRET_KEY=<paste: openssl rand -hex 32>
POSTGRES_PASSWORD=<a strong password>
GROQ_API_KEY=<your groq key>
FAL_API_KEY=<your fal key>
IMAGE_GEN_PROVIDER=fal
VIDEO_GEN_PROVIDER=fal
RETRIEVAL_ENABLED=true
SEED_CURRICULUM=1
SEED_DEMO=1
```

> `PUBLIC_URL` is compiled into the web app **at build time**, so it must be
> correct before you build. If you change the domain later, rebuild the web
> image (`docker compose -f docker-compose.prod.yml build web`).

---

## 4. Deploy

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

First boot takes a few minutes (builds both images, downloads the embedding
model, runs migrations, seeds the demo classroom + curriculum, and Caddy
fetches a TLS cert). Watch it:

```bash
docker compose -f docker-compose.prod.yml logs -f api caddy
```

When the API logs `Application startup complete` and Caddy shows a certificate
obtained, open **https://$DOMAIN**.

---

## 5. Pre-flight — verify BEFORE the demo

```bash
# From the VM (or anywhere), run the golden-path smoke test:
docker compose -f docker-compose.prod.yml exec api python /scripts/smoke_test.py \
  --base-url https://$DOMAIN
```

Then click through manually (all logins password **`Demo1234!`**):

- [ ] **https://$DOMAIN** loads over HTTPS (padlock, no cert warning).
- [ ] **Student** `kid5@demo.roognis.ai` → AI Tutor → ask *"How do I add 1/2 and
      1/4?"* → answer streams in **with an illustration** (image gen works).
- [ ] Ask for a **video** on an answer → an explainer clip generates (Fal video).
- [ ] With curriculum RAG on, a Maths question returns a **cited** answer
      (sources panel shows the seeded chapters).
- [ ] Take a **quiz** → submit → see results.
- [ ] **Teacher** `teacher@demo.roognis.ai` → Grade 8 Mathematics → class
      analytics show all 5 students across the mastery range.
- [ ] **Parent** `parent@demo.roognis.ai` → sees Aarav's progress.
- [ ] No-auth demo mode: opening the site fresh drops you straight into the
      portal (no login wall).

If image/video are slow or flaky on the day, set `IMAGE_GEN_PROVIDER=stub` and
`VIDEO_GEN_PROVIDER=stub` in `.env`, `up -d` again, and the tutor still works
(placeholders instead of generated media).

---

## 6. Demo-day checklist

- [ ] Deployed + smoke-tested **by July 18** (buffer for surprises).
- [ ] Fal + Groq keys have credit; check the Fal dashboard for balance.
- [ ] A backup laptop / tethered hotspot in case venue wifi is bad.
- [ ] The [10-minute demo script](DEMO.md#6-suggested-demo-script-10-min) rehearsed.
- [ ] Screenshot/recording of a successful run as a fallback if live fails.

---

## 7. Costs (rough, for the demo month)

| | Est. |
|---|---|
| VM (8 GB) | ~$15–48 / mo |
| Groq | cents per demo |
| Fal (images + video) | a few dollars for rehearsals + demo |
| Domain (optional) | ~$10 / yr, or free via sslip.io |

---

## 8. Operate

```bash
# logs
docker compose -f docker-compose.prod.yml logs -f api
# restart after an .env change (no rebuild needed unless PUBLIC_URL changed)
docker compose -f docker-compose.prod.yml up -d
# full rebuild (after code changes)
docker compose -f docker-compose.prod.yml up -d --build
# stop
docker compose -f docker-compose.prod.yml down
```

Data (Postgres, Qdrant, uploads, TLS certs) lives in named Docker volumes and
survives restarts. `down` keeps volumes; `down -v` wipes them (don't, unless
you want a fresh seed).
