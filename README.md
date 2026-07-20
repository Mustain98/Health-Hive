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

**LLM key rotation.** The core backend spreads load across up to three Groq keys (`GROQ_API_KEY`, `GROQ_API_KEY_2`, `GROQ_API_KEY_3`). Each request starts on the *next* key in the pool, so no single key absorbs all traffic, and a rate-limited key fails over to the preferred model on another key before ever degrading to the fallback model. All of this lives in `app/core/llm/`; a single key works fine too. Note Groq rate-limits per *organization* — keys from the same account share a limit.

### Backend: a modular monolith

```
backend/app/
├── core/       # cross-cutting: auth, database, llm/, embeddings, enums, units, logging
├── modules/    # domain modules — one folder per bounded context
├── agents/     # the AI layer (see below)
├── utils/      # small pure helpers (calculate, text, time)
├── models.py   # imports every table so SQLModel.metadata is complete
└── routes.py   # the one aggregator; mounts every module router under /api
```

Each **module** owns its bounded context and is split the same way — `models/`, `schemas/`,
`services/`, `routers/`, and `controllers/` where request orchestration is worth separating
from business logic. Every router carries its own prefix, so moving one between modules
never changes a URL.

| Module | Responsibility |
|---|---|
| `user` | Accounts, auth (JWT + Google), body metrics, health profile |
| `milestone` | Long-term aims (lose weight, gain muscle, …) + the **risk classifier** (`services/risk.py`) and safe-target suggester (`services/suggest.py`) |
| `daily_goal` | Habits, per-day completion logs, and their own risk guard |
| `daily_log` | Calories in/out, deficit/surplus, streaks |
| `nutrition_target` | Daily calories + macros, TDEE-derived |
| `meal_plan_setting` | How a day's meals split — slots, percentages, labels |
| `plan` | Groups milestone + daily goals + nutrition target + meal setting into one activatable **Plan** (one active per user, DB-enforced) |
| `meal` | Food items, meals, labels, embeddings tables |
| `consultant` | Consultant profiles, onboarding applications, credential documents |
| `consultation` | **Pre-booking**: request → chat → time proposal → books an appointment |
| `appointment` | **The booked session**: appointments, session rooms, video, and post-session follow-up rooms |
| `notification` | In-app notification center (bell, unread counts, deep links) |

A deliberate domain distinction runs through the booking system — three concepts that are never conflated:
**request** (a pending "knock" with no chat) → **consultation chat** (created only when the consultant replies) → **room/session** (created only when a time proposal is accepted).

### The agent layer

`backend/app/agents/` holds the LLM-driven work. The organising idea is that **agent
autonomy is rationed** — the more freedom a call has, the more machinery guards it — so
there are three tiers rather than one uniform swarm:

| Tier | What it is | Where | Guarded by |
|---|---|---|---|
| **1. Conversational agent** | A real tool loop: the model decides which tools to call and when, over many turns | `setup_chat` | Specialist routing, per-turn call limit, tool retries, approval gating, risk guard |
| **2. Single-shot calls** | One call in, one result out. No tool loop, no memory, no middleware | `finalize`, `meal_plan/agent`, `enrichment/agent`, and the two `suggest.py` helpers in `modules/` — all via `structured(Schema)`. `summarize` is the odd one out: plain `model_chain()` returning free text | Strict bounded schemas — invalid output raises before it reaches the DB |
| **3. Deterministic code** | No LLM at all | combo assembly, `services/risk.py`, `proposal.validate_items` | Ordinary tests |

Only tier 1 is agentic in the "decides its own next step" sense. Tiers 2 and 3 are what
the decisions get checked against — **the LLM thinks, deterministic code decides.**

#### How a chat turn actually runs

```
user message
   │
   ▼
turn_router.route_turn()          keyword match, no LLM — routing must not cost a call
   │                              picks 1 of 5 specialists; ambiguous → coach
   ▼
specialist = its own prompt + its own TOOLS subset
   │
   │   all five share a 4-tool core:
   │     propose_plan_changes · list_plans · continue_draft_plan · start_new_draft_plan
   │
   │   and each adds only what it needs:
   │     milestone   (5)  + get_health_data
   │     meals       (5)  + get_current_setup
   │     nutrition   (6)  + get_current_setup, get_health_data
   │     daily_goals (6)  + get_current_setup, list_daily_goals
   │     coach       (9)  + all of the above, and the two cross-session memory tools
   ▼
create_agent(model=chain(llm_candidates()), tools, system_prompt, middleware, checkpointer?)
   │
   │  middleware stack, outermost first:
   │    TokenUsageMiddleware ······ per-session token accounting
   │    ModelCallLimitMiddleware ·· 25 model calls per turn, then stop
   │    ToolRetryMiddleware ······· 2 retries, then continue with the error
   │    SummarizationMiddleware ··· compress past 30 messages, keep 10 verbatim
   │    HumanInTheLoopMiddleware ·· only when the chat has approval mode on
   ▼
tool loop ──▶ propose_plan_changes ──▶ validate_items()   ← risk guard, BEFORE the user is asked
   │                                        │
   │                                   invalid → error + safe values back to the model,
   │                                             which corrects itself in the same turn
   ▼
SSE frames: delta / reset / interrupt / choice / done
```

Two design choices worth calling out:

- **Routing narrows the tool surface, not just the prompt.** A `milestone` turn never sees
  the meal tools, so the model can't wander into them. The cost of a mis-route is bounded
  because the fallback (`coach`) holds every tool — a wrong guess is slower, never broken.
- **One batch write tool, not nine.** Every mutation goes through `propose_plan_changes`,
  which is why nine habits proposed across nine model calls still arrive as one approval
  card — and why there is exactly one place to put the risk guard and the draft-plan guard.

#### The other workflow: meal generation is a pipeline, not a loop

`meal_plan` is agentic in a different shape — the model is called **once**, at the one step
where judgement helps, and everything downstream is deterministic:

```
1. resolve the daily macro target        active NutritionTarget, or TDEE + LLM suggestion
2. LLM: one constraint per meal slot      macros · composition · labels · retrieval query
        ── the only creative step, and the only one that can be wrong ──
3. embed the query → pgvector search      + hard allergen / diet filters (never advisory)
4. deterministic assembler                builds & selects combos that hit the numbers
5. persist                                variety across days by rotating the chosen option
```

Steps 1–2 run **once per generation** and are reused across days.

Note where the safety filters sit. The model *is* told your allergies and diet preferences
(they're in the profile it gets at step 2), but that's advisory — enforcement is a hard
post-retrieval filter in `build_pool`, which drops any meal whose ingredient set intersects
your allergen food-items, and any meal whose ingredient labels intersect the disallowed set
for your diet. Deterministic, and it runs whether the model cooperated or not. So a
hallucinated label costs you a worse meal, never an unsafe one — the belt-and-braces being
deliberate, since asking a model nicely is not an allergen control.

`enrichment` is the third agent and runs offline: it writes the LLM health-context blurb
and the embedding that step 3 retrieves each meal *by*. Nothing in the request path waits
on it.

#### Reliability: every LLM call has a way to fail

Each tier degrades differently, on purpose:

| Path | When the model fails | Why that choice |
|---|---|---|
| Key/model chain (all calls) | Next key, then next model — `k1/main → k2/main → k3/main → k1/fallback → …` | Groq rate-limits per *organization*; rotating keys spreads load, and a rate-limited key tries the *preferred* model elsewhere before degrading |
| Meal-plan constraints | Deterministic fallback constraints | A plan built from defaults beats no plan |
| Meal retrieval | Non-semantic SQL pool (`_fallback_pool_ids`) | Embedding API down shouldn't block dinner |
| Meal enrichment | `_fallback()` blurb | Enrichment is a background nicety |
| Session summarize | Returns `""`, never raises | A missing session preview must not fail closing the chat |
| **Finalize** | **Raises** — no fallback at all | Deliberately loud: a malformed plan must fail, not persist something plausible-looking |

⚠️ One wrinkle there: `finalize.py`'s docstring says the caller turns a schema failure into
a **422**, but [`router.py`](backend/app/agents/setup_chat/router.py) actually catches it as
a **500**. A bad LLM parse is a validation failure, not a server fault, so the 500 is
arguably wrong — but the behaviour is the 500, and the docstring is the stale part.

#### Boundaries

The intended rule is that agents import from `modules/` but not from each other — shared
prompts live with the domain module that owns the shape (e.g.
`nutrition_target/services/suggest.py`), which is why the macro and meal-structure prompts
sit there rather than in an agent, and why `modules/` contains LLM calls at all.

⚠️ **That rule is currently broken in four places** — worth knowing before you move code:

```
meal_plan/service.py   → enrichment.agent
enrichment/agent.py    → meal_plan.embeddings      (circular with the line above)
setup_chat/service.py  → meal_plan.service (assemble_profile, _coerce_meal_time)
setup_chat/tools.py    → meal_plan.service (_coerce_meal_time)
```

Two of those reach for a *private* helper (`_coerce_meal_time`) across an agent boundary.
The fix is to move the shared pieces down into the owning module — `_coerce_meal_time`
belongs with `meal_plan_setting`, and the embedding text helpers belong in
`core/embeddings.py` — but nothing depends on that happening first.

| Agent | Responsibility |
|---|---|
| `setup_chat` | The plan-setup coach — streaming chat, tool registry, human-in-the-loop approvals, risk guard, finalize |
| `meal_plan` | LLM constraint generation → pgvector retrieval → deterministic combo assembly |
| `enrichment` | Writes the LLM health-context blurb + embedding each meal is retrieved by |

Inside `setup_chat`, the pieces worth knowing:

| File | Role |
|---|---|
| `service.py` | Turn orchestration and the SSE stream (`stream_turn`, `resume_turn`) |
| `tools.py` | The tool registry the model calls — one batch write tool, the rest read-only |
| `specialists/` | Five per-intent system prompts (`coach`, `milestone`, `daily_goals`, `nutrition`, `meals`); `turn_router.py` picks one per turn |
| `proposal.py` | Validates a proposed batch **before** the user is asked, so the risk guard never refuses something already approved |
| `hitl.py` | "Ask before saving" — LangGraph interrupt config + the Postgres checkpointer holding a suspended run |
| `finalize.py` / `summarize.py` | Conversation → structured drafts; session → rolling memory |

---

## ✨ Features & Functionality

### 🤖 AI Plan-Setup Coach (the flagship)
A streaming, tool-using chatbot (`/plan-setup`) that behaves like a real coach:

- **Coach-first behavior** — it analyzes, explains its rationale, and discusses before writing anything; it only persists changes on your explicit confirmation.
- **Tool-based context** — instead of dumping your profile into every prompt, the LLM calls tools (`get_health_data`, `get_current_setup`, `get_past_session_summaries`, …) only when it needs them. General questions never touch your PII.
- **Specialist routing** — each turn is routed to one of five focused prompts (coach / milestone / daily goals / nutrition / meals) instead of one giant system prompt, so a turn only pays for the rules it needs.
- **One batch write tool** — every change goes through `propose_plan_changes`, which can carry several items at once. That is what lets nine habits proposed across nine model calls arrive as **one** approval card with nine rows, and it is validated *before* you're asked, so the risk guard never refuses something you already approved.
- **Full chat-driven CRUD** — "change my pushups to squats" edits that habit; "I want to bulk instead" recomputes your TDEE-derived nutrition target and confirms. Milestones, daily goals, nutrition targets, and meal structures can all be created, edited, and deleted from chat.
- **"Ask before saving" (optional, per chat)** — with approval mode on, every write pauses and you approve / edit / reject each item. *Edit* keeps the idea and re-proposes it corrected; *reject* stops it being proposed again unchanged. The suspended run lives in a LangGraph Postgres checkpointer, so it survives across requests and processes.
- **Draft-plan picker** — when a write would land in an ambiguous place (you have several drafts and this chat isn't pointed at one), the chat shows the reusable drafts as **clickable cards plus "create new"** rather than asking in prose. Picking one points the chat at it and immediately continues the change you asked for. Cards are identified by their *contents* and date, since AI drafts share a name.
- **Cross-session memory** — sessions are summarized on close; the coach can recall past conversations or reference a specific transcript.
- **Guided ordered flow** — milestone → daily goals → nutrition target (derived from the goal) → meal structure, confirming each step.
- **Everything lands as an inactive draft Plan** — reviewed in a draft panel and activated as a unit.

**The chat's SSE contract.** `POST /api/plan-setup/sessions/{id}/messages` streams
`data: {…}` frames the client applies in order:

| Frame | Meaning |
|---|---|
| `{"delta": "…"}` | Append text to the current assistant bubble |
| `{"reset": true}` | What streamed so far was narration *before* a tool call — clear the bubble and start over |
| `{"interrupt": {"requests": […]}}` | Approval mode: these writes need a decision. Answer via `POST …/resume` |
| `{"choice": {"kind": "choose_draft_plan", …}}` | Render the draft-plan picker; the click pins via `PATCH …/draft-plan` or `POST …/new-draft-plan` |
| `{"error": "…"}` | Turn failed |
| `{"done": true, …}` | Terminal frame, carries message count and session status |

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
│   ├── app/core/    #   auth · database · llm · embeddings · enums · units
│   ├── app/modules/ #   user · milestone · daily_goal · daily_log · nutrition_target
│   │                #   · meal_plan_setting · plan · meal · consultant · consultation
│   │                #   · appointment · notification
│   ├── app/agents/  #   setup_chat · meal_plan · enrichment
│   ├── alembic/     #   migrations (alterations only — see the convention below)
│   └── tests/       #   plain scripts, no pytest: `python tests/<name>.py`
├── adminfrontend/   # Admin app — Next.js (:3001)
├── adminbackend/    # Admin API — FastAPI (moderation, verification, content)
│                    #   fully independent — its own app/ tree, shares only the DB + JWTs
├── docs/            # Design records: REFACTOR_PLAN, PLAN_SETUP_AGENT_REBUILD
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

### Tests

Backend tests are **plain scripts, not pytest** — each is runnable on its own and exits
non-zero on failure, so no test runner is a dependency. They build their own in-memory
SQLite database via `tests/harness.py`, so none of them touch your real database:

```bash
cd backend && python tests/test_setup_chat_safety.py
```

Every check in `test_setup_chat_safety.py` names a defect seen in a real user session
(see `docs/PLAN_SETUP_AGENT_REBUILD.md`) — add a case there when you fix an agent bug.

Frontend correctness is covered by the compiler: `npx tsc --noEmit` and `npm run build`.

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
