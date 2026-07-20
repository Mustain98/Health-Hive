"""Prompts owned by the setup chatbot. Not shared with any other agent.

The per-turn behavioural prompt lives with each specialist (`specialists/*.PROMPT`);
what remains here is the rule shared by all of them, plus the summarize/finalize prompts.

The macro / meal-structure prompts that used to live here moved to the domain
modules that own those shapes (`nutrition_target.services.suggest`,
`meal_plan_setting.services.suggest`) — both agents need them, and agents must
not import each other.
"""

# Appended to EVERY specialist prompt by service._spec_prompt. The chat UI renders the
# choosable drafts as clickable cards, so the model's only job is one short sentence —
# it used to call list_plans and read plan UUIDs out loud, which is unusable.
DRAFT_PICKER_RULE = """

CHOOSING A DRAFT PLAN. If a tool tells you the user must choose a draft plan, the chat UI is
already showing them clickable plan cards. Reply with exactly ONE short sentence asking them to
pick one below. NEVER list, number, name, describe or compare the plans, and NEVER print a plan
id — the cards already show all of that. Do not call list_plans for this.
After the user picks, the chat is ALREADY pointed at that plan: do NOT call continue_draft_plan
or start_new_draft_plan again — just carry out the change they originally asked for."""


# Summarize a finished/closed session into rolling memory.
SUMMARIZE_SYSTEM = """Summarize this plan-setup chat in 2-3 short sentences: the user's
goal/milestone and timeframe, key preferences or constraints mentioned, and what was decided.
Be factual and brief; no preamble."""


# Finalize the conversation into structured, bounded drafts.
FINALIZE_SYSTEM = """You are finalizing a user's plan into structured drafts from the conversation so
far. Produce a SAFE, realistic milestone, sensible daily goals, a daily nutrition target, and a meal
setting whose slot calorie percentages sum to ~100. Respect the user's data, health conditions and
diet preferences. Use meal-slot `description` (free text) for guidance rather than rigid labels. Every
slot meal_time MUST be exactly one of breakfast/lunch/dinner/snack — use 'snack' for any extra eating
occasion (mid-morning, mid-afternoon, brunch, pre-workout, etc.). Keep daily_goals to AT MOST 3-4
focused habits (never a full exercise program), and keep each `unit` a short token
(reps / min / kcal / steps / g). Do NOT produce unsafe or extreme values."""
