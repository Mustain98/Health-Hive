# 🐝 Health Hive

**Your entire health journey — one hive.** AI-coached goal setting, personalized meal planning, daily habit tracking, and real human experts, all in a single platform.

---

## 🚀 The Pitch

Most health apps solve one slice of the problem. A calorie counter doesn't know your goal. A meal planner doesn't know your medical conditions. A telehealth app doesn't know what you ate this week. Users end up stitching together four apps that never talk to each other — and quit all of them.

**Health Hive closes the loop.** It combines:

1. **An AI health coach** that interviews you conversationally, understands your body metrics and health conditions, and drafts a complete, personalized plan — milestone, daily habits, nutrition targets, and meal structure — in one chat.
2. **An AI meal-planning engine** that turns that plan into real daily menus using LLM-generated constraints, semantic retrieval over a curated meal database, and deterministic combo assembly — so plans are creative *and* nutritionally exact.
3. **A human expert marketplace** — verified consultants (nutritionists, trainers, physicians) you can message, negotiate a time with in chat, and meet over built-in video. When the AI detects a risky goal, it doesn't guess — **it refers you to a human**.
4. **Daily accountability** — goal logging, calorie in/out tracking, streaks, deficits, and notifications that keep the plan alive after day one.

The safety philosophy is baked into the architecture: **the AI drafts, the human decides.** Every AI-generated plan is created *inactive* until the user reviews and activates it, and any risky request (extreme deficits, medical red flags) is blocked at the service layer and routed to a consultant — no matter which entry point it came from.

---

## 🏗️ System Architecture

Health Hive is four deployable applications sharing one PostgreSQL database:

```
┌─────────────────────┐        ┌─────────────────────┐
│   User Frontend      │        │   Admin Frontend     │
│   Next.js 16 / React │        │   Next.js / React    │
│   :3000              │        │   :3001              │
└──────────┬───────────┘        └──────────┬───────────┘
           │ REST /api                     │ REST /api/admin
           ▼                               ▼
┌─────────────────────┐        ┌─────────────────────┐
│   Core Backend       │        │   Admin Backend      │
│   FastAPI + SQLModel │        │   FastAPI            │
│   modular monolith   │        │   moderation & CMS   │
└──────────┬───────────┘        └──────────┬───────────┘
           │                               │
           ▼                               ▼
┌──────────────────────────────────────────────────────┐
│         PostgreSQL (Supabase) + pgvector              │
│   users · plans · meals · embeddings · consultations  │
└──────────────────────────────────────────────────────┘

External services:
  🧠 Groq (Llama 3.3 70B, GPT-OSS-120B fallback) — LLM reasoning via LangChain
  🔎 Jina (jina-embeddings-v3, 1024-dim)          — meal embeddings via API
  🎥 Agora                                        — live video consultations
  📦 Supabase Storage                             — documents & meal images
```

### Tech stack

| Layer | Technology |
|---|---|
| User & Admin UI | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts, Framer Motion |
| API | FastAPI, SQLModel/SQLAlchemy, Pydantic, Alembic |
| Auth | JWT (python-jose) + Argon2 password hashing, role-based guards (user / consultant / admin) |
| AI | Core backend: LangChain + Groq (`llama-3.3-70b-versatile`, `openai/gpt-oss-120b` fallback), structured outputs with strict Pydantic validation. Admin backend: raw `groq` SDK for AI-assisted food-item generation |
| Vector search | pgvector + Jina embeddings (`jina-embeddings-v3`, 1024-dim) |
| Realtime video | Agora RTC (token server built in) |
| Streaming chat | Server-Sent Events (SSE) |

**LLM key rotation.** The core backend spreads load across up to three Groq keys (`GROQ_API_KEY`, `GROQ_API_KEY_2`, `GROQ_API_KEY_3`). Each request starts on the *next* key in the pool, so no single key absorbs all traffic, and a rate-limited key fails over to the preferred model on another key before ever degrading to the fallback model. All of this lives in `_llm_candidates()` (`meal_planner_agent/llm.py`); a single key works fine too. Note Groq rate-limits per *organization* — keys from the same account share a limit.

### Backend: a modular monolith

The core backend (`backend/app/modules/`) is organized into self-contained modules, each with its own `models`, `schemas`, `service`, and `router`:

| Module | Responsibility |
|---|---|
| `user` | Accounts, auth, body metrics, goals/milestones, daily goals & logs, nutrition targets, **risk classifier** |
| `plan` | Groups milestone + daily goals + nutrition target + meal setting into one activatable **Plan** (one active per user, DB-enforced) |
| `meal` | Food items, meals, labels, meal-plan settings, embeddings tables |
| `meal_planner_agent` | The AI brain: setup chatbot, LLM constraint generation, semantic retrieval, plan generation, tools |
| `consultant` | Consultant profiles, onboarding applications, credential documents |
| `consultation` | **Pre-booking**: request → chat → time proposal → books an appointment |
| `appointment` | **The booked session**: appointments, session rooms, video, and post-session follow-up rooms |
| `notification` | In-app notification center (bell, unread counts, deep links) |

A deliberate domain distinction runs through the booking system — three concepts that are never conflated:
**request** (a pending "knock" with no chat) → **consultation chat** (created only when the consultant replies) → **room/session** (created only when a time proposal is accepted).

---

## ✨ Features & Functionality

### 🤖 AI Plan-Setup Coach (the flagship)
A streaming, tool-using chatbot (`/plan-setup`) that behaves like a real coach:

- **Coach-first behavior** — it analyzes, explains its rationale, and discusses before writing anything; it only persists changes on your explicit confirmation.
- **Tool-based context** — instead of dumping your profile into every prompt, the LLM calls tools (`get_health_data`, `get_current_setup`, `get_past_session_summaries`, …) only when it needs them. General questions never touch your PII.
- **Full chat-driven CRUD** — "change my pushups to squats" calls `update_daily_goal`; "I want to bulk instead" recomputes your TDEE-derived nutrition target and confirms. Milestones, daily goals, nutrition targets, and meal structures can all be created, edited, and deleted from chat.
- **Cross-session memory** — sessions are summarized on close; the coach can recall past conversations or reference a specific transcript.
- **Guided ordered flow** — milestone → daily goals → nutrition target (derived from the goal) → meal structure, confirming each step.
- **Everything lands as an inactive draft Plan** — reviewed in a draft panel and activated as a unit.

### 🍽️ AI Meal-Plan Generation
A hybrid pipeline where **the LLM thinks and deterministic code decides**:

1. The LLM generates *per-meal-slot constraints* — macro splits, composition rules (main/side/dessert), required and preferred labels, condition-driven nutrient limits (e.g. sodium caps), and a natural-language retrieval query.
2. That query is embedded via the **Jina embeddings API** and run through **pgvector semantic search** over an AI-enriched meal database (each meal carries an LLM-written health context).
3. A deterministic assembler picks meal combos that actually hit the numbers — with a full deterministic fallback so generation **never hard-fails**, even if the LLM does.

A meal plan is a **recurring Mon–Sun template, not a calendar week** — days are weekdays (`day_of_week`, Mon=0 … Sun=6, the same convention as daily goals), never dates. Each user has exactly one week plan holding up to seven day plans, enforced in the DB.

**Day intersection.** Generating days that are *already planned* doesn't silently clobber them: the requested days ∩ the already-planned days come back as a 409 listing the conflicting meal slots. You then choose per-slot which to overwrite; everything you don't pick is kept, and the requested days that had no plan are created fresh.

Generation is **gated**: no active nutrition target + meal setting → a structured 409 offers "set up with AI" or "talk to a consultant." No silent defaults.

### 🎯 Milestones, Daily Goals & Accountability
- **Milestones** (lose weight, gain muscle, …) with dynamic typed attributes (hybrid columns + validated JSON).
- **Daily goals** with per-day completion logs, plus a daily log form: calories in/out → live deficit/surplus, computed on the *client's* local date (no server-timezone streak bugs).
- **Plans as a unit** — activate a plan and its milestone, daily goals, target, and meal setting go live together; exactly one active plan per user, enforced by partial unique indexes at the DB level.
- Notification bell with unread badges, "log your day" reminders, and deep links.

### 🛡️ Safety by Architecture
- `is_risky()` runs in the **service layer** on *every* activation path — manual CRUD, chatbot, and generation alike. Risky goals get a 4xx with a consultant referral; the AI path short-circuits to "please talk to a professional."
- LLM output is treated as **untrusted input**: finalized plans are parsed against strict Pydantic schemas with numeric bounds before the risk check, and rejected if malformed or out of range.
- AI drafts are always `active=False` until a human activates them.

### 👩‍⚕️ Consultant Marketplace & Booking
- Browse verified consultants; consultants onboard via an application + credential documents reviewed by admins.
- **Chat-based booking**: send a request describing your issue → consultant replies (opens a chat) or declines → either side proposes a time → acceptance books an appointment and creates a session room automatically.
- **Live video sessions** over Agora with in-session chat.
- **Follow-up rooms** for post-consultation messaging and rescheduling — kept separate from pre-booking chat.
- Consultants get their own workspace: manage clients, view their daily goals, plans, and log history.

### 🧑‍💼 Admin Platform (separate app)
- Platform stats, user management (activate/suspend).
- Consultant verification: review applications and credential documents.
- Content management: food items and meals with labels, nutrition data, image upload — including **AI-assisted food-item generation**.

---

## 🔄 Key Flows

### 1. Onboarding → Active Plan (the AI path)

```
Sign up → enter body metrics & health data
   │
   ▼
Open the Plan-Setup Coach (/plan-setup)
   │  streaming chat; LLM pulls context via tools on demand
   ▼
Discuss: milestone → daily goals → nutrition → meal structure
   │  (risky ask? → refused + consultant referral, nothing persisted)
   ▼
Finalize → strict schema validation → risk guard
   │
   ▼
One DRAFT Plan (all parts inactive) + "setup ready" notification
   │
   ▼
User reviews the draft panel → Activate plan (as a unit)
   │  previous active plan auto-deactivates
   ▼
Meal-plan generation gate lifts → daily menus available
```

### 2. Meal generation (weekday-based)

```
POST /api/meal-plans/generate-day    { "day_of_week": 0-6 }   (default: today)
POST /api/meal-plans/generate-week   { "days": [0..6] }        (default: all seven)
   │  gate: active NutritionTarget + MealPlanSetting? ──no──▶ 409 {needs_setup, options}
   ▼ yes
   │  day intersection: requested days ∩ already-planned days
   │     └─ non-empty ──▶ 409 {overlap, days, conflicts}
   │                       user picks which slots to overwrite, re-POSTs with
   │                       overwrite_timed_meal_ids → those regenerate, rest kept
   ▼ no conflict
LLM: per-slot constraints (macros, composition, labels, limits, retrieval query)
   ▼
Jina embeddings + pgvector: semantic retrieval over enriched meals
   ▼
Deterministic assembler: pick combos that hit the macros
   ▼
Day plan (with rationale per slot) — deterministic fallback if the LLM fails
```

Other meal-plan routes: `POST /timed-meal/{id}/regenerate`, `POST /day/{id}/regenerate`,
`POST /timed-meal/{id}/swap`, the delete routes, and `GET /api/meal-plans/me`.

### 3. Booking a consultant

```
User: POST /consultations/requests {consultant, issue}     (pending — no chat yet)
Consultant: decline ──▶ done (no chat)
            reply   ──▶ ConsultationChat opens, seeded with issue + reply
Both: chat freely
Either: propose a time slot
Other: accept ──▶ Appointment(scheduled) + SessionRoom created
   ▼
Scheduled video session (Agora) → post-session Follow-Up room
```

### 4. Daily accountability loop

```
Morning: "Log your day" notification
   ▼
Daily log form: tick daily goals, enter calories in / out
   ▼
Live deficit/surplus vs. your target → streaks & charts
   ▼
Coach chat can read progress and adjust goals via tools — on your confirmation
```

---

## 📁 Repository Layout

Everything lives on `main` — one branch, four deployable apps.

```
Health Hive/
├── frontend/        # User app — Next.js (dashboard, plans, daily goals, plan-setup
│                    #   chat, meal plan, consultants, consultations, sessions, video)
├── backend/         # Core API — FastAPI modular monolith (run: uvicorn main:app)
│   └── app/modules/ #   user · plan · meal · meal_planner_agent · consultant
│                    #   · consultation · appointment · notification
├── adminfrontend/   # Admin app — Next.js (:3001)
├── adminbackend/    # Admin API — FastAPI (moderation, verification, content)
└── render.yaml      # Render blueprint — all four services, one per rootDir
```

The two APIs share **one Supabase Postgres database** and the **same JWTs**, so
`SECRET_KEY` / `ALGORITHM` must be identical in both. The **core backend owns the schema** —
`create_db_and_tables()` and Alembic run there and only there; the admin API only reads and
writes existing tables.

## 🏁 Getting Started

**Prerequisites:** Python 3.11+, Node 20+, a PostgreSQL database with the `pgvector` extension (Supabase works out of the box), a Groq API key, a **Jina API key** (meal embeddings), and Agora credentials.

```bash
# Core backend  → http://localhost:8000
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# create .env — see the env-var table below
alembic upgrade head          # schema alterations (tables auto-create on startup)
uvicorn main:app --reload

# User frontend → http://localhost:3000
cd frontend && npm install && npm run dev

# Admin backend → http://localhost:8001
cd adminbackend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# Admin frontend → http://localhost:3001
cd adminfrontend && npm install && npm run dev -- -p 3001
```

### Environment variables

`backend/.env`:

| Var | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string (needs the `pgvector` extension) |
| `SECRET_KEY`, `ALGORITHM` | JWT signing (e.g. `HS256`) |
| `GROQ_API_KEY` | LLM reasoning — **required** |
| `GROQ_API_KEY_2`, `GROQ_API_KEY_3` | Optional extra keys; requests round-robin across whatever is set |
| `JINA_API_KEY` | Meal embeddings — required for semantic retrieval |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | Storage (documents & meal images) |
| `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `AGORA_TOKEN_TTL_SECONDS` | Video consultations |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | "Sign in with Google" (authorization-code flow) — the backend exchanges the code and verifies the ID token. Optional; omit to disable Google sign-in |

`adminbackend/.env`:

| Var | Purpose |
|---|---|
| `SECRET_KEY`, `ALGORITHM` | **Must match the core backend** — it validates the same JWTs |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | All admin reads/writes go through Supabase |
| `GROQ_API_KEY` | AI-assisted food-item generation (raw `groq` SDK; no key rotation here) |

`CORS_ORIGINS` (both APIs, optional): comma-separated full origins of the deployed frontends, e.g.
`https://healthhive-web.onrender.com,https://healthhive-admin-web.onrender.com`. `localhost:3000/3001`
are always allowed on top of it.

`NEXT_PUBLIC_API_URL` (both frontends): full URL of the API each one talks to (defaults to
`http://127.0.0.1:8000` / `:8001`).
It is baked into the client bundle at **build** time, so changing it needs a rebuild.

`NEXT_PUBLIC_GOOGLE_CLIENT_ID` (user frontend, optional): the Google OAuth client ID for the
"Sign in with Google" button — **the same value** as the backend's `GOOGLE_CLIENT_ID`. Also
baked in at build time. Unset it and the button simply doesn't render (password login still
works). Google sign-in uses the **authorization-code (redirect) flow**: the button sends the
user to Google, which returns to `/auth/google/callback`, which posts the code to the backend.
Register that path as an **Authorized redirect URI** on the OAuth client in Google Cloud Console
(`https://<your-frontend>/auth/google/callback`, plus `http://localhost:3000/auth/google/callback`
for local dev).

The admin apps' env vars are documented on the `admin` branch.

**Migration convention:** new tables are created idempotently on startup via `create_db_and_tables()`; Alembic migrations cover only alterations (columns, indexes, constraints) to existing tables.

---

## 🧭 Design Principles

1. **AI drafts, humans activate.** Generation and activation are always separate steps.
2. **Risk checks live in the service layer** — every entry point is guarded, not just the AI.
3. **LLM output is untrusted** — strict bounded schemas before anything persists.
4. **LLM thinks, code decides** — creative constraint generation, deterministic assembly, always a fallback.
5. **One source of truth** — planned ≠ consumed; your daily log is authoritative for progress, never auto-derived from the plan.
6. **Humans in the loop where it matters** — risky cases route to verified consultants, and consultants are first-class citizens of the product, not an afterthought.

---

*Health Hive — plan smart, eat right, stay accountable, and know when to call a Expert.* 🐝
