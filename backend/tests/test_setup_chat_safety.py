"""Safety and persistence behaviour of the setup-chat tools.

Every case here is a defect observed in a real user session (see
docs/PLAN_SETUP_AGENT_REBUILD.md), so each test names the symptom it prevents.

Run: python tests/test_setup_chat_safety.py
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select  # noqa: E402

from tests.harness import Results, make_engine  # noqa: E402
from app.modules.milestone.models import Milestone  # noqa: E402
from app.modules.daily_goal.models import DailyGoal  # noqa: E402
from app.modules.user.models import UserData  # noqa: E402
from app.modules.plan.models import Plan  # noqa: E402
from app.agents.setup_chat.models import PlanSetupSession  # noqa: E402
from app.modules.milestone.schemas import GoalType, MilestoneType  # noqa: E402
from app.modules.milestone.services import risk  # noqa: E402
from app.modules.milestone.services.suggest import propose_milestone  # noqa: E402
from app.agents.setup_chat import tools as setup_tools  # noqa: E402

r = Results("setup-chat safety")
engine = make_engine()
USER = uuid.uuid4()


def seed(db, *, height_cm=170.0, weight_kg=51.7):
    db.add(UserData(user_id=USER, age=25, gender="male", height_cm=height_cm,
                    weight_kg=weight_kg, activity_level="moderate"))
    s = PlanSetupSession(user_id=USER)
    db.add(s)
    db.commit()
    db.refresh(s)
    plan = Plan(created_for=USER, created_by=USER, source="ai", name="AI plan", active=False)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    s.draft_plan_id = plan.id
    db.add(s)
    db.commit()
    return s, plan


# ── safe_bounds: the envelope the AI plans inside ──────────────────────────
r.section("safe_bounds for the reported user (170 cm, 51.7 kg)")
b = risk.safe_bounds(170, 51.7)
r.check("BMI is 17.89", b["current_bmi"] == 17.89, str(b["current_bmi"]))
r.check("classified underweight", b["bmi_status"] == "underweight")
r.check("healthy floor is 53.5 kg", b["min_healthy_weight_kg"] == 53.5, str(b["min_healthy_weight_kg"]))
r.check("healthy ceiling is 72.0 kg", b["max_healthy_weight_kg"] == 72.0, str(b["max_healthy_weight_kg"]))
r.check("max weekly gain is 0.5 kg", b["max_weekly_gain_kg"] == 0.5)
r.check("60 kg needs 119 days, not the 56 the agent proposed",
        risk.min_safe_duration_days(51.7, 60.0) == 119,
        str(risk.min_safe_duration_days(51.7, 60.0)))

# ── propose_milestone is safe by construction ──────────────────────────────
r.section("every deterministic proposal passes the guard")
with Session(engine) as db:
    seed(db)
    for h, w, muscle in [(170, 51.7, True), (170, 51.7, False), (170, 95, False),
                         (170, 120, False), (170, 65, True), (170, 65, False)]:
        ud = db.exec(select(UserData).where(UserData.user_id == USER)).first()
        ud.height_cm, ud.weight_kg = h, w
        db.add(ud)
        db.commit()
        p = propose_milestone(h, w, wants_muscle=muscle)
        m = Milestone(created_for=USER, created_by=USER, active=False,
                      goal_type=GoalType.maintain,
                      milestone_type=MilestoneType(p["milestone_type"]),
                      name=p["name"], target_weight=p["target_weight"],
                      target_value=p["target_muscle_kg"], initial_weight=w,
                      duration_days=p["duration_days"])
        reason = risk.is_risky_milestone(db, USER, m)
        r.check(f"{h}cm/{w}kg muscle={muscle} -> {p['milestone_type']} "
                f"target={p['target_weight']} in {p['duration_days']}d is safe",
                reason is None, reason or "")

# ── the dirty-flush bug: "not saved" must mean not saved ───────────────────
r.section("a rejected unsafe edit does not survive in the session")
engine2 = make_engine()
with Session(engine2) as db:
    s, plan = seed(db)
    safe = Milestone(created_for=USER, created_by=USER, active=False,
                     goal_type=GoalType.gain, milestone_type=MilestoneType.gain_weight,
                     name="Healthy weight gain", target_weight=54.9, initial_weight=51.7,
                     duration_days=56, plan_id=plan.id)
    db.add(safe)
    db.commit()
    db.refresh(safe)
    safe_id = safe.id

    registry = setup_tools.build_tool_registry(db, USER, None, setup_session_id=s.id)
    # The exact edit from the transcript: 60 kg in 56 days = 1.05 kg/wk (cap 0.5).
    out = registry["set_milestone"](milestone_type="gain_muscle",
                                    name="Healthy weight gain and muscle",
                                    target_weight=60, duration_days=56)
    r.check("the unsafe edit is refused", "error" in out, str(out.get("error", ""))[:70])
    r.check("refusal carries safe_bounds so the model can self-correct", "safe_bounds" in out)
    r.check("refusal carries the minimum safe duration",
            out.get("min_safe_duration_days_for_this_target") == 119,
            str(out.get("min_safe_duration_days_for_this_target")))
    # THE BUG: a later commit in the same session used to flush the dirty mutation.
    db.add(PlanSetupSession(user_id=USER))
    db.commit()

with Session(engine2) as db:
    row = db.get(Milestone, safe_id)
    r.check("target_weight still 54.9 after a later commit", row.target_weight == 54.9,
            str(row.target_weight))
    r.check("duration_days still 56", row.duration_days == 56, str(row.duration_days))
    r.check("name unchanged", row.name == "Healthy weight gain", repr(row.name))
    r.check("stored row still passes the guard", risk.is_risky_milestone(db, USER, row) is None)

# ── a safe milestone still saves normally ──────────────────────────────────
r.section("the safe proposal saves")
engine3 = make_engine()
with Session(engine3) as db:
    s, plan = seed(db)
    registry = setup_tools.build_tool_registry(db, USER, None, setup_session_id=s.id)
    p = propose_milestone(170, 51.7, wants_muscle=True)
    out = registry["set_milestone"](milestone_type=p["milestone_type"], name=p["name"],
                                    target_weight=p["target_weight"],
                                    target_value=p["target_muscle_kg"], unit="kg",
                                    duration_days=p["duration_days"])
    r.check("saves without error", out.get("ok") is True, str(out.get("error", "")))
    r.check("stored target is the safe 54.9 kg", out.get("milestone", {}).get("target_weight") == 54.9,
            str(out.get("milestone", {}).get("target_weight")))

# ── daily goals: unsafe drafts are refused, not deferred to activation ─────
r.section("unsafe daily goals are refused at draft time")
engine4 = make_engine()
with Session(engine4) as db:
    s, plan = seed(db)
    registry = setup_tools.build_tool_registry(db, USER, None, setup_session_id=s.id)
    bad = registry["add_daily_goal"](name="Marathon steps", goal_type="steps",
                                     target_value=99999, unit="steps")
    r.check("an absurd step target is refused while still a draft", "error" in bad,
            str(bad.get("error", ""))[:60])
    good = registry["add_daily_goal"](name="Back Squat", goal_type="exercise",
                                      target_value=3, unit="sets", days_of_week=[0, 2, 4])
    r.check("a sensible habit still saves", good.get("ok") is True, str(good.get("error", "")))
    r.check("it lands on THIS chat's draft plan",
            db.get(DailyGoal, uuid.UUID(good["daily_goal"]["id"])).plan_id == plan.id)

# ── dedup must not hijack a habit from an older plan ───────────────────────
r.section("dedup is scoped to the current draft plan")
engine5 = make_engine()
with Session(engine5) as db:
    s, plan = seed(db)
    old_plan = Plan(created_for=USER, created_by=USER, source="ai", name="older", active=False)
    db.add(old_plan)
    db.commit()
    db.refresh(old_plan)
    old_goal = DailyGoal(created_for=USER, created_by=USER, goal_type="exercise",
                         name="Back Squat", target_value=3, unit="sets", active=False,
                         plan_id=old_plan.id)
    db.add(old_goal)
    db.commit()
    db.refresh(old_goal)
    old_id, old_target = old_goal.id, old_goal.target_value

    registry = setup_tools.build_tool_registry(db, USER, None, setup_session_id=s.id)
    out = registry["add_daily_goal"](name="Back Squat", goal_type="exercise",
                                     target_value=5, unit="sets")
    r.check("adding the same-named habit succeeds", out.get("ok") is True, str(out.get("error", "")))
    new_id = uuid.UUID(out["daily_goal"]["id"])
    r.check("it is a NEW row on this plan, not the old plan's row", new_id != old_id)
    r.check("the new row belongs to this chat's draft plan",
            db.get(DailyGoal, new_id).plan_id == plan.id)
    db.expire_all()
    r.check("the older plan's habit is untouched",
            db.get(DailyGoal, old_id).target_value == old_target,
            str(db.get(DailyGoal, old_id).target_value))

r.finish()
