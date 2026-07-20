// Shared display formatting for goals and milestones.
//
// Why this exists: daily goals store their real detail (reps, rep ranges, hold time,
// per-leg) in `attributes`, but every list rendered only `target_value + unit` — so a
// goal saved as "3 sets × 10 reps" displayed as just "3 sets". One formatter, used by
// the daily-goals page, the plans page and the approval card, keeps the story whole.

export const WEEKDAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

type GoalLike = {
    target_value?: number | null;
    unit?: string | null;
    days_of_week?: number[] | null;
    attributes?: Record<string, unknown> | null;
};

/** "3 sets × 10 reps" / "3 sets × 8–12 reps" / "3 × 30s hold" / "30 min" — plus per-leg. */
export function formatGoalDetail(g: GoalLike): string {
    const a = (g.attributes || {}) as Record<string, unknown>;
    const parts: string[] = [];

    if (g.target_value != null) {
        const base = `${g.target_value} ${g.unit || ""}`.trim();
        if (typeof a.hold_time_sec === "number") {
            parts.push(`${g.target_value} × ${a.hold_time_sec}s hold`);
        } else if (typeof a.reps === "number") {
            parts.push(`${base} × ${a.reps} reps`);
        } else if (typeof a.reps_min === "number" && typeof a.reps_max === "number") {
            parts.push(`${base} × ${a.reps_min}–${a.reps_max} reps`);
        } else {
            parts.push(base);
        }
    } else if (typeof a.reps === "number") {
        parts.push(`${a.reps} reps`);
    }

    if (a.per_leg === true) parts.push("per leg");
    if (typeof a.note === "string" && a.note.trim()) parts.push(a.note.trim());
    return parts.join(" · ");
}

/** "Mon, Wed, Fri" — or "every day" when unscheduled. */
export function formatDays(days?: number[] | null): string {
    if (!days || days.length === 0) return "every day";
    return days.map((d) => WEEKDAY_SHORT[d] ?? String(d)).join(", ");
}

/** "today 14:32" / "yesterday" / "3 days ago" / "12 Jul" — for telling apart records
 * that are otherwise identical (e.g. draft plans, all of which are named "AI plan"). */
export function formatRelativeDate(iso?: string | null): string {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    const startOfDay = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const days = Math.round((startOfDay(new Date()) - startOfDay(d)) / 86_400_000);
    if (days <= 0) return `today ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    if (days === 1) return "yesterday";
    if (days < 7) return `${days} days ago`;
    return d.toLocaleDateString([], { day: "numeric", month: "short" });
}

export const MILESTONE_TYPE_LABELS: Record<string, string> = {
    lose_weight: "Lose weight",
    gain_weight: "Gain weight",
    gain_muscle: "Gain muscle",
    maintain: "Maintain",
    recomposition: "Body recomposition",
    custom: "Custom",
};

export function milestoneTypeLabel(t?: string | null): string {
    if (!t) return "";
    return MILESTONE_TYPE_LABELS[t] ?? t.replace(/_/g, " ");
}

/** Friendly names for the write tools shown on the approval card. */
export const TOOL_LABELS: Record<string, string> = {
    add_daily_goal: "Daily goal",
    update_daily_goal: "Update daily goal",
    delete_daily_goal: "Delete daily goal",
    set_milestone: "Milestone",
    delete_milestone: "Delete milestone",
    set_nutrition_target: "Nutrition target",
    delete_nutrition_target: "Delete nutrition target",
    set_meal_setting: "Meal setting",
    delete_meal_setting: "Delete meal setting",
};
