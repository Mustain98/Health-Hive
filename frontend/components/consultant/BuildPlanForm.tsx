"use client";

import { useState, FormEvent } from "react";
import { apiFetch } from "@/lib/api";
import type { MilestoneType, DailyGoalType } from "@/lib/types";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MILESTONE_TYPES: MilestoneType[] = ["lose_weight", "gain_weight", "gain_muscle", "maintain"];
const DG_TYPES: DailyGoalType[] = ["exercise", "calorie_burn", "intake", "steps", "custom"];
const MEAL_TIMES = ["breakfast", "lunch", "dinner", "snack"];

interface BuildDailyGoal { name: string; goal_type: DailyGoalType; target_value: string; unit: string; days_of_week: number[]; }
interface BuildSlot { name: string; meal_time: string; calories_pct: string; }

/** Consultant form that composes a whole INACTIVE plan for a client
 *  (milestone + daily goals + nutrition target + meal setting) via
 *  POST /api/consultant/users/{userId}/plans. */
export function BuildPlanForm({ userId, onCreated, onError }: {
    userId: string;
    onCreated?: () => void;
    onError?: (msg: string) => void;
}) {
    const [planName, setPlanName] = useState("Consultant plan");
    const [withMilestone, setWithMilestone] = useState(true);
    const [msForm, setMsForm] = useState({ milestone_type: "lose_weight" as MilestoneType, name: "", target_weight: "", target_value: "", unit: "kg", duration_days: "" });
    const [buildGoals, setBuildGoals] = useState<BuildDailyGoal[]>([]);
    const [withTarget, setWithTarget] = useState(true);
    const [targetForm, setTargetForm] = useState({ calories_kcal: "", protein_g: "", carbs_g: "", fat_g: "" });
    const [withMeals, setWithMeals] = useState(false);
    const [mealName, setMealName] = useState("Consultant meal plan");
    const [slots, setSlots] = useState<BuildSlot[]>([
        { name: "Breakfast", meal_time: "breakfast", calories_pct: "25" },
        { name: "Lunch", meal_time: "lunch", calories_pct: "35" },
        { name: "Dinner", meal_time: "dinner", calories_pct: "30" },
        { name: "Snack", meal_time: "snack", calories_pct: "10" },
    ]);
    const [building, setBuilding] = useState(false);

    async function submitPlan(e: FormEvent) {
        e.preventDefault();
        setBuilding(true);
        const payload: Record<string, any> = { name: planName.trim() || "Consultant plan" };
        if (withMilestone) {
            payload.milestone = {
                milestone_type: msForm.milestone_type,
                name: msForm.name.trim() || null,
                target_weight: msForm.target_weight ? Number(msForm.target_weight) : null,
                target_value: msForm.target_value ? Number(msForm.target_value) : null,
                unit: msForm.unit || null,
                duration_days: msForm.duration_days ? Number(msForm.duration_days) : null,
            };
        }
        if (buildGoals.length) {
            payload.daily_goals = buildGoals
                .filter((g) => g.name.trim())
                .map((g) => ({
                    name: g.name.trim(), goal_type: g.goal_type,
                    target_value: g.target_value ? Number(g.target_value) : null,
                    unit: g.unit || null,
                    days_of_week: g.days_of_week.length ? g.days_of_week : null,
                }));
        }
        if (withTarget) {
            payload.nutrition_target = {
                calories_kcal: targetForm.calories_kcal ? Number(targetForm.calories_kcal) : null,
                protein_g: targetForm.protein_g ? Number(targetForm.protein_g) : null,
                carbs_g: targetForm.carbs_g ? Number(targetForm.carbs_g) : null,
                fat_g: targetForm.fat_g ? Number(targetForm.fat_g) : null,
            };
        }
        if (withMeals) {
            payload.meal_setting = {
                name: mealName.trim() || "Consultant meal plan",
                timed_meals_per_day: slots.length,
                timed_meals: slots.map((s) => ({
                    name: s.name.trim(), meal_time: s.meal_time,
                    calories_pct: s.calories_pct ? Number(s.calories_pct) : 0,
                })),
            };
        }
        try {
            await apiFetch(`/api/consultant/users/${userId}/plans`, { method: "POST", body: payload });
            onCreated?.();
        } catch (err: any) {
            onError?.(err.message || "Failed to create plan");
        } finally {
            setBuilding(false);
        }
    }

    return (
        <form onSubmit={submitPlan} className="space-y-6">
            <p className="text-sm text-gray-500">Everything is saved <b>inactive</b> — the client reviews and activates the plan themselves.</p>
            <div>
                <label className="block text-xs font-medium text-gray-500">Plan name</label>
                <input value={planName} onChange={(e) => setPlanName(e.target.value)} className="mt-1 w-full sm:w-80 rounded-md border border-gray-300 px-3 py-2 text-sm" />
            </div>

            {/* Milestone */}
            <div className="border border-gray-100 rounded-lg p-4 space-y-3">
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-800">
                    <input type="checkbox" checked={withMilestone} onChange={(e) => setWithMilestone(e.target.checked)} className="h-4 w-4" />
                    🎯 Milestone
                </label>
                {withMilestone && (
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        <div>
                            <label className="block text-xs text-gray-500">Type</label>
                            <select value={msForm.milestone_type} onChange={(e) => setMsForm({ ...msForm, milestone_type: e.target.value as MilestoneType })} className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm capitalize">
                                {MILESTONE_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs text-gray-500">Name (optional)</label>
                            <input value={msForm.name} onChange={(e) => setMsForm({ ...msForm, name: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm" />
                        </div>
                        <div>
                            <label className="block text-xs text-gray-500">Target weight (kg)</label>
                            <input type="number" value={msForm.target_weight} onChange={(e) => setMsForm({ ...msForm, target_weight: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm" />
                        </div>
                        <div>
                            <label className="block text-xs text-gray-500">Target value</label>
                            <input type="number" value={msForm.target_value} onChange={(e) => setMsForm({ ...msForm, target_value: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm" />
                        </div>
                        <div>
                            <label className="block text-xs text-gray-500">Unit</label>
                            <input value={msForm.unit} onChange={(e) => setMsForm({ ...msForm, unit: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm" />
                        </div>
                        <div>
                            <label className="block text-xs text-gray-500">Duration (days)</label>
                            <input type="number" value={msForm.duration_days} onChange={(e) => setMsForm({ ...msForm, duration_days: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm" />
                        </div>
                    </div>
                )}
            </div>

            {/* Daily goals */}
            <div className="border border-gray-100 rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-gray-800">✅ Daily goals</p>
                    <button type="button" onClick={() => setBuildGoals([...buildGoals, { name: "", goal_type: "exercise", target_value: "", unit: "reps", days_of_week: [] }])}
                        className="text-xs px-3 py-1.5 rounded-md bg-blue-50 text-blue-700 font-medium hover:bg-blue-100">+ Add goal</button>
                </div>
                {buildGoals.length === 0 && <p className="text-xs text-gray-400">No daily goals added.</p>}
                {buildGoals.map((g, i) => (
                    <div key={i} className="border border-gray-100 rounded-md p-3 space-y-2">
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                            <input placeholder="name e.g. Treadmill" value={g.name} onChange={(e) => setBuildGoals(buildGoals.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} className="rounded-md border border-gray-300 px-2 py-1.5 text-sm" />
                            <select value={g.goal_type} onChange={(e) => setBuildGoals(buildGoals.map((x, j) => j === i ? { ...x, goal_type: e.target.value as DailyGoalType } : x))} className="rounded-md border border-gray-300 px-2 py-1.5 text-sm capitalize">
                                {DG_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
                            </select>
                            <input type="number" placeholder="target" value={g.target_value} onChange={(e) => setBuildGoals(buildGoals.map((x, j) => j === i ? { ...x, target_value: e.target.value } : x))} className="rounded-md border border-gray-300 px-2 py-1.5 text-sm" />
                            <input placeholder="unit" value={g.unit} onChange={(e) => setBuildGoals(buildGoals.map((x, j) => j === i ? { ...x, unit: e.target.value } : x))} className="rounded-md border border-gray-300 px-2 py-1.5 text-sm" />
                        </div>
                        <div className="flex items-center gap-1.5 flex-wrap">
                            {DAY_LABELS.map((label, d) => (
                                <button key={label} type="button"
                                    onClick={() => setBuildGoals(buildGoals.map((x, j) => j === i ? { ...x, days_of_week: x.days_of_week.includes(d) ? x.days_of_week.filter((y) => y !== d) : [...x.days_of_week, d] } : x))}
                                    className={`px-2 py-0.5 text-xs rounded-full border ${g.days_of_week.includes(d) ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 border-gray-300"}`}>
                                    {label}
                                </button>
                            ))}
                            <span className="text-xs text-gray-400 ml-1">none = every day</span>
                            <button type="button" onClick={() => setBuildGoals(buildGoals.filter((_, j) => j !== i))} className="ml-auto text-xs text-red-500 hover:text-red-700">remove</button>
                        </div>
                    </div>
                ))}
            </div>

            {/* Nutrition target */}
            <div className="border border-gray-100 rounded-lg p-4 space-y-3">
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-800">
                    <input type="checkbox" checked={withTarget} onChange={(e) => setWithTarget(e.target.checked)} className="h-4 w-4" />
                    🥗 Nutrition target
                </label>
                {withTarget && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        {([["calories_kcal", "Calories (kcal)"], ["protein_g", "Protein (g)"], ["carbs_g", "Carbs (g)"], ["fat_g", "Fat (g)"]] as const).map(([k, label]) => (
                            <div key={k}>
                                <label className="block text-xs text-gray-500">{label}</label>
                                <input type="number" value={targetForm[k]} onChange={(e) => setTargetForm({ ...targetForm, [k]: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm" />
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Meal setting */}
            <div className="border border-gray-100 rounded-lg p-4 space-y-3">
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-800">
                    <input type="checkbox" checked={withMeals} onChange={(e) => setWithMeals(e.target.checked)} className="h-4 w-4" />
                    🍽 Meal setting
                </label>
                {withMeals && (
                    <div className="space-y-2">
                        <input value={mealName} onChange={(e) => setMealName(e.target.value)} placeholder="setting name" className="w-full sm:w-80 rounded-md border border-gray-300 px-2 py-1.5 text-sm" />
                        {slots.map((s, i) => (
                            <div key={i} className="grid grid-cols-4 gap-2 items-center">
                                <input value={s.name} onChange={(e) => setSlots(slots.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} className="rounded-md border border-gray-300 px-2 py-1.5 text-sm" />
                                <select value={s.meal_time} onChange={(e) => setSlots(slots.map((x, j) => j === i ? { ...x, meal_time: e.target.value } : x))} className="rounded-md border border-gray-300 px-2 py-1.5 text-sm capitalize">
                                    {MEAL_TIMES.map((t) => <option key={t} value={t}>{t}</option>)}
                                </select>
                                <input type="number" value={s.calories_pct} onChange={(e) => setSlots(slots.map((x, j) => j === i ? { ...x, calories_pct: e.target.value } : x))} className="rounded-md border border-gray-300 px-2 py-1.5 text-sm" placeholder="% kcal" />
                                <button type="button" onClick={() => setSlots(slots.filter((_, j) => j !== i))} className="text-xs text-red-500 hover:text-red-700 text-left">remove</button>
                            </div>
                        ))}
                        <button type="button" onClick={() => setSlots([...slots, { name: "Snack", meal_time: "snack", calories_pct: "10" }])} className="text-xs px-3 py-1.5 rounded-md bg-blue-50 text-blue-700 font-medium hover:bg-blue-100">+ Add slot</button>
                    </div>
                )}
            </div>

            <button type="submit" disabled={building} className="px-5 py-2.5 text-sm font-semibold rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">
                {building ? "Creating…" : "Create plan for client"}
            </button>
        </form>
    );
}
