// The contents of one plan — milestone, nutrition target, meal setting, daily goals.
//
// Extracted from the plan-setup page's "Draft plans" list so the draft PICKER renders
// its slots with exactly the same body. Every AI draft is literally named "AI plan"
// (backend plan.py hardcodes it), so contents are the only way to tell drafts apart —
// which makes one shared renderer worth having.
//
// Contents only: the caller owns the card frame and any header actions.

import type { PlanRead } from "@/lib/types";
import { milestoneTypeLabel } from "@/lib/format";

/** A one-line fingerprint of what's in a plan: "Gain weight · 2600 kcal · 4 meals · 3 goals". */
export function planSignature(p: PlanRead): string {
    const bits: string[] = [];
    if (p.milestone) {
        bits.push([milestoneTypeLabel(p.milestone.milestone_type), p.milestone.name]
            .filter(Boolean).join(" — "));
    }
    if (p.nutrition_target) bits.push(`${p.nutrition_target.calories_kcal} kcal`);
    if (p.meal_setting) {
        const n = p.meal_setting.timed_meals?.length ?? p.meal_setting.timed_meals_per_day;
        bits.push(`${n} ${n === 1 ? "meal" : "meals"}`);
    }
    const dg = p.daily_goals?.length ?? 0;
    if (dg) bits.push(`${dg} ${dg === 1 ? "goal" : "goals"}`);
    return bits.join(" · ");
}

/** True when the plan has no parts at all — an unused shell.
 *
 * Checks all FOUR parts itself rather than reading `missing`: the backend's `missing`
 * only tracks milestone/nutrition_target/meal_setting and never daily_goals, so a plan
 * holding nothing but daily goals reports `missing: []` and would read as non-empty. */
export function planIsEmpty(p: PlanRead): boolean {
    return !p.milestone && !p.nutrition_target && !p.meal_setting
        && (p.daily_goals?.length ?? 0) === 0;
}

/** `compact` trims the meal-slot detail so picker cards stay scannable. */
export function PlanSummary({ plan: p, compact = false }: { plan: PlanRead; compact?: boolean }) {
    const meals = p.meal_setting?.timed_meals ?? [];
    return (
        <div className="space-y-3 text-sm text-gray-700">
            <div>
                <div className="font-semibold text-gray-800">🎯 Milestone</div>
                {p.milestone ? (
                    <div className="pl-5 text-gray-600">
                        <p className="capitalize">{(p.milestone.milestone_type || "").replace(/_/g, " ")} {p.milestone.name ? ` — ${p.milestone.name}` : ""}</p>
                        <p className="text-xs text-gray-500">
                            {p.milestone.target_weight ? `target ${p.milestone.target_weight} kg` : ""}
                            {p.milestone.target_value ? ` · ${p.milestone.target_value} ${p.milestone.unit || ""}` : ""}
                            {p.milestone.duration_days ? ` · ${p.milestone.duration_days} days` : ""}
                        </p>
                    </div>
                ) : <span className="text-gray-400 pl-5">no milestone</span>}
            </div>

            <div>
                <div className="font-semibold text-gray-800">🍽️ Nutrition Target</div>
                {p.nutrition_target ? (
                    <p className="pl-5 text-gray-600">{p.nutrition_target.calories_kcal} kcal · P{Math.round(p.nutrition_target.protein_g)} C{Math.round(p.nutrition_target.carbs_g)} F{Math.round(p.nutrition_target.fat_g)}</p>
                ) : <span className="text-gray-400 pl-5">no nutrition target</span>}
            </div>

            <div>
                <div className="font-semibold text-gray-800">📋 Meal Setting {p.meal_setting ? `· ${p.meal_setting.name}` : ""}</div>
                {!p.meal_setting ? (
                    <span className="text-gray-400 pl-5">no meal setting</span>
                ) : compact ? (
                    <p className="pl-5 text-xs text-gray-600">
                        {meals.length
                            ? meals.map((m) => `${m.meal_time} ${Math.round(m.calories_pct)}%`).join(" · ")
                            : `${p.meal_setting.timed_meals_per_day} meals/day`}
                    </p>
                ) : (
                    <ul className="pl-5 space-y-1 list-disc list-inside text-gray-600">
                        {meals.map((m, i) => (
                            <li key={i} className="text-xs">
                                <span className="font-medium text-gray-700">{m.meal_time}</span> · {Math.round(m.calories_pct)}%
                                {(m.protein_g_pct !== undefined || m.carbs_g_pct !== undefined || m.fat_g_pct !== undefined) && (
                                    <span className="text-gray-400 ml-1">(P{m.protein_g_pct ?? m.calories_pct}% C{m.carbs_g_pct ?? m.calories_pct}% F{m.fat_g_pct ?? m.calories_pct}%)</span>
                                )}
                                {m.meal_labels && m.meal_labels.length > 0 && (
                                    <span className="text-indigo-400 ml-1">[{m.meal_labels.join(", ")}]</span>
                                )}
                                {m.description && <span className="text-gray-500 ml-1">— {m.description}</span>}
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            <div>
                <div className="font-semibold text-gray-800">✅ Daily Goals</div>
                {p.daily_goals && p.daily_goals.length > 0 ? (
                    <ul className="pl-5 space-y-1 list-disc list-inside text-gray-600">
                        {p.daily_goals.map((dg) => (
                            <li key={dg.id} className="text-xs">{dg.name}{dg.target_value ? ` — ${dg.target_value} ${dg.unit || ""}` : ""}</li>
                        ))}
                    </ul>
                ) : <span className="text-gray-400 pl-5">no daily goals</span>}
            </div>

            {p.missing.length > 0 && (
                <p className="text-xs font-medium text-amber-600 bg-amber-50 px-3 py-1.5 rounded-lg inline-block">
                    Missing: {p.missing.map((m) => m.replace(/_/g, " ")).join(", ")}
                </p>
            )}
        </div>
    );
}
