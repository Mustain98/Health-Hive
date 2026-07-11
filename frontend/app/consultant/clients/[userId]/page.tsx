"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api";
import { LogHistoryTable } from "@/components/ui/LogHistoryTable";
import { BuildPlanForm } from "@/components/consultant/BuildPlanForm";
import type {
    GoalRead,
    PlanRead,
    DailyLogHistoryDay,
} from "@/lib/types";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const formatDays = (days: number[] | null | undefined) =>
    !days || days.length === 0 ? "Every day" : [...days].sort((a, b) => a - b).map((d) => DAY_LABELS[d]).join(", ");

interface ClientDailyGoal {
    id: string; name: string; goal_type: string; target_value: number | null;
    unit: string | null; active: boolean; days_of_week: number[] | null;
    attributes: Record<string, any>; plan_id: string | null; created_at: string;
}

interface NutritionTargetDto {
    id: string; calories_kcal: number | null; protein_g: number | null;
    carbs_g: number | null; fat_g: number | null; active: boolean;
}

interface MealSettingDto {
    id: string; name: string; timed_meals_per_day: number; active: boolean;
    timed_meals: { name: string; meal_time: string; calories_pct: number; description?: string | null }[];
}

type Tab = "plans" | "goals" | "details" | "build";

export default function ClientDetailPage() {
    const params = useParams();
    const userId = String(params.userId); // UUID — keep as string

    const [tab, setTab] = useState<Tab>("plans");
    const [noAccess, setNoAccess] = useState(false);
    const [loading, setLoading] = useState(true);
    const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

    const [plans, setPlans] = useState<PlanRead[]>([]);
    const [dailyGoals, setDailyGoals] = useState<ClientDailyGoal[]>([]);
    const [history, setHistory] = useState<DailyLogHistoryDay[]>([]);
    const [milestone, setMilestone] = useState<GoalRead | null>(null);
    const [target, setTarget] = useState<NutritionTargetDto | null>(null);
    const [mealSetting, setMealSetting] = useState<MealSettingDto | null>(null);

    async function loadAll() {
        setLoading(true);
        setNoAccess(false);
        const results = await Promise.allSettled([
            apiFetch<PlanRead[]>(`/api/consultant/users/${userId}/plans`),
            apiFetch<ClientDailyGoal[]>(`/api/consultant/users/${userId}/daily-goals`),
            apiFetch<DailyLogHistoryDay[]>(`/api/consultant/users/${userId}/daily-goal-logs`),
            apiFetch<GoalRead>(`/api/consultant/users/${userId}/goal`),
            apiFetch<NutritionTargetDto | null>(`/api/consultant/users/${userId}/nutrition-target`),
            apiFetch<MealSettingDto | null>(`/api/consultant/users/${userId}/meal-plan-setting`),
        ]);
        const [pl, dg, hist, ms, nt, mps] = results;
        if (results.some((r) => r.status === "rejected" && r.reason instanceof ApiError && r.reason.status === 403)) {
            setNoAccess(true);
        }
        if (pl.status === "fulfilled") setPlans(pl.value);
        if (dg.status === "fulfilled") setDailyGoals(dg.value);
        if (hist.status === "fulfilled") setHistory(hist.value);
        if (ms.status === "fulfilled") setMilestone(ms.value);
        if (nt.status === "fulfilled") setTarget(nt.value);
        if (mps.status === "fulfilled") setMealSetting(mps.value);
        setLoading(false);
    }

    useEffect(() => { loadAll(); }, [userId]); // eslint-disable-line react-hooks/exhaustive-deps

    if (loading) return <div className="text-center py-12 text-gray-500">Loading client data…</div>;

    if (noAccess) {
        return (
            <div className="max-w-2xl mx-auto bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
                <p className="text-yellow-800 font-medium">You don&apos;t have access to this client.</p>
                <p className="text-sm text-yellow-700 mt-1">
                    Access requires an active follow-up or a session the client hasn&apos;t revoked.
                </p>
            </div>
        );
    }

    const TABS: { key: Tab; label: string }[] = [
        { key: "plans", label: "📦 Plans" },
        { key: "goals", label: "✅ Daily goals & logs" },
        { key: "details", label: "🎯 Milestone · Nutrition · Meals" },
        { key: "build", label: "🛠 Build plan" },
    ];

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Client overview</h1>
                <p className="mt-1 text-sm text-gray-500">Client ID: {userId.substring(0, 8)}…</p>
            </div>

            {message && (
                <div className={`px-4 py-3 rounded-md border text-sm ${message.type === "success" ? "bg-green-50 text-green-800 border-green-200" : "bg-red-50 text-red-800 border-red-200"}`}>
                    {message.text}
                </div>
            )}

            <div className="flex flex-wrap gap-2 border-b border-gray-200">
                {TABS.map((t) => (
                    <button key={t.key} onClick={() => setTab(t.key)}
                        className={`px-4 py-2 text-sm font-medium rounded-t-md ${tab === t.key ? "bg-white border border-gray-200 border-b-white text-blue-700 -mb-px" : "text-gray-500 hover:text-gray-800"}`}>
                        {t.label}
                    </button>
                ))}
            </div>

            {/* ── Plans ── */}
            {tab === "plans" && (
                <div className="space-y-4">
                    {plans.length === 0 && <p className="text-sm text-gray-400 bg-white rounded-lg shadow p-6">No plans yet — build one in the &quot;Build plan&quot; tab.</p>}
                    {plans.map((p) => (
                        <div key={p.id} className="bg-white shadow rounded-lg p-5 space-y-3">
                            <div className="flex items-center gap-2 flex-wrap">
                                <h3 className="text-lg font-semibold text-gray-900">{p.name}</h3>
                                <span className="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200 capitalize">{p.source}</span>
                                {p.active
                                    ? <span className="text-xs px-2 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-200">Active</span>
                                    : <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">Inactive</span>}
                                {p.missing?.length > 0 && (
                                    <span className="text-xs text-amber-600">missing: {p.missing.join(", ")}</span>
                                )}
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
                                <div className="border border-gray-100 rounded-lg p-3">
                                    <p className="text-xs font-medium text-gray-400 mb-1">🎯 Milestone</p>
                                    {p.milestone ? (
                                        <p className="text-gray-800">
                                            <span className="capitalize">{(p.milestone.milestone_type || "").replace("_", " ")}</span>
                                            {p.milestone.target_weight ? ` · ${p.milestone.target_weight} kg` : ""}
                                            {p.milestone.target_value ? ` · ${p.milestone.target_value} ${p.milestone.unit || ""}` : ""}
                                            {p.milestone.duration_days ? ` · ${p.milestone.duration_days}d` : ""}
                                        </p>
                                    ) : <p className="text-gray-400">—</p>}
                                </div>
                                <div className="border border-gray-100 rounded-lg p-3">
                                    <p className="text-xs font-medium text-gray-400 mb-1">🥗 Nutrition</p>
                                    {p.nutrition_target ? (
                                        <p className="text-gray-800">{p.nutrition_target.calories_kcal} kcal · P{p.nutrition_target.protein_g} C{p.nutrition_target.carbs_g} F{p.nutrition_target.fat_g}</p>
                                    ) : <p className="text-gray-400">—</p>}
                                </div>
                                <div className="border border-gray-100 rounded-lg p-3">
                                    <p className="text-xs font-medium text-gray-400 mb-1">🍽 Meal setting</p>
                                    {p.meal_setting ? (
                                        <p className="text-gray-800">{p.meal_setting.name} · {p.meal_setting.timed_meals_per_day}/day</p>
                                    ) : <p className="text-gray-400">—</p>}
                                </div>
                                <div className="border border-gray-100 rounded-lg p-3">
                                    <p className="text-xs font-medium text-gray-400 mb-1">✅ Daily goals</p>
                                    {p.daily_goals.length ? (
                                        <p className="text-gray-800">{p.daily_goals.map((d) => d.name).join(", ")}</p>
                                    ) : <p className="text-gray-400">—</p>}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* ── Daily goals & logs ── */}
            {tab === "goals" && (
                <div className="space-y-6">
                    <div className="bg-white shadow rounded-lg p-5">
                        <h3 className="text-lg font-semibold text-gray-900 mb-3">Daily goals</h3>
                        {dailyGoals.length === 0 ? <p className="text-sm text-gray-400">None.</p> : (
                            <div className="space-y-2">
                                {dailyGoals.map((g) => (
                                    <div key={g.id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-100">
                                        <div className="flex-1">
                                            <p className="text-sm font-medium text-gray-800">{g.name}</p>
                                            <p className="text-xs text-gray-400 capitalize">
                                                {g.goal_type.replace("_", " ")}
                                                {g.target_value != null ? ` · ${g.target_value} ${g.unit || ""}` : ""}
                                                {` · ${formatDays(g.days_of_week)}`}
                                            </p>
                                        </div>
                                        {g.active
                                            ? <span className="text-xs px-2 py-0.5 rounded-full bg-green-50 text-green-700">active</span>
                                            : <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">inactive</span>}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="bg-white shadow rounded-lg p-5">
                        <h3 className="text-lg font-semibold text-gray-900 mb-3">Log history (last 30 days)</h3>
                        <LogHistoryTable history={history} />
                    </div>
                </div>
            )}

            {/* ── Milestone / Nutrition / Meal setting ── */}
            {tab === "details" && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <div className="bg-white shadow rounded-lg p-5">
                        <h3 className="font-semibold text-gray-900 mb-2">🎯 Milestone</h3>
                        {milestone ? (
                            <div className="text-sm text-gray-700 space-y-1">
                                <p className="capitalize font-medium">{(milestone.milestone_type || milestone.goal_type || "").toString().replace("_", " ")}</p>
                                {milestone.name && <p>{milestone.name}</p>}
                                {milestone.target_weight != null && <p>Target weight: {milestone.target_weight} kg</p>}
                                {milestone.target_value != null && <p>Target: {milestone.target_value} {milestone.unit || ""}</p>}
                                {milestone.duration_days != null && <p>Duration: {milestone.duration_days} days</p>}
                                <p className="text-xs text-gray-400">{milestone.active ? "Active" : "Inactive"}</p>
                            </div>
                        ) : <p className="text-sm text-gray-400">No milestone set.</p>}
                    </div>
                    <div className="bg-white shadow rounded-lg p-5">
                        <h3 className="font-semibold text-gray-900 mb-2">🥗 Nutrition target</h3>
                        {target ? (
                            <div className="text-sm text-gray-700 space-y-1">
                                <p className="font-medium">{target.calories_kcal} kcal/day</p>
                                <p>Protein {target.protein_g} g · Carbs {target.carbs_g} g · Fat {target.fat_g} g</p>
                                <p className="text-xs text-gray-400">{target.active ? "Active" : "Inactive"}</p>
                            </div>
                        ) : <p className="text-sm text-gray-400">No active nutrition target.</p>}
                    </div>
                    <div className="bg-white shadow rounded-lg p-5">
                        <h3 className="font-semibold text-gray-900 mb-2">🍽 Meal setting</h3>
                        {mealSetting ? (
                            <div className="text-sm text-gray-700 space-y-1">
                                <p className="font-medium">{mealSetting.name} · {mealSetting.timed_meals_per_day} meals/day</p>
                                {mealSetting.timed_meals?.map((tm, i) => (
                                    <p key={i} className="text-xs text-gray-500 capitalize">{tm.meal_time}: {tm.name} ({tm.calories_pct}%)</p>
                                ))}
                            </div>
                        ) : <p className="text-sm text-gray-400">No active meal setting.</p>}
                    </div>
                </div>
            )}

            {/* ── Build plan ── */}
            {tab === "build" && (
                <div className="bg-white shadow rounded-lg p-5">
                    <BuildPlanForm
                        userId={userId}
                        onCreated={async () => {
                            setMessage({ text: "Plan created — the client can now review and activate it ✅", type: "success" });
                            setTab("plans");
                            await loadAll();
                        }}
                        onError={(msg) => setMessage({ text: msg, type: "error" })}
                    />
                </div>
            )}
        </div>
    );
}

