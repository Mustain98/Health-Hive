"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { PlanRead } from "@/lib/types";

const SOURCE_BADGE: Record<string, { label: string; cls: string }> = {
    self: { label: "You", cls: "bg-gray-100 text-gray-600" },
    ai: { label: "AI", cls: "bg-indigo-100 text-indigo-700" },
    consultant: { label: "Consultant", cls: "bg-blue-100 text-blue-700" },
};
const MISSING_LABEL: Record<string, string> = {
    milestone: "milestone", nutrition_target: "nutrition target", meal_setting: "meal setting",
};

export default function PlansPage() {
    const [plans, setPlans] = useState<PlanRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState<string | null>(null);
    const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

    async function load() {
        try { setPlans(await apiFetch<PlanRead[]>("/api/plans")); }
        catch (e: any) { setMessage({ text: e.message, type: "error" }); }
        finally { setLoading(false); }
    }
    useEffect(() => { load(); }, []);

    async function act(plan: PlanRead, action: "activate" | "deactivate" | "delete") {
        if (action === "delete" && !confirm(`Delete plan "${plan.name}" and all its parts?`)) return;
        setBusy(plan.id); setMessage(null);
        try {
            if (action === "delete") await apiFetch(`/api/plans/${plan.id}`, { method: "DELETE" });
            else await apiFetch(`/api/plans/${plan.id}/${action}`, { method: "PATCH" });
            await load();
            setMessage({ text: `Plan ${action}d.`, type: "success" });
        } catch (e: any) { setMessage({ text: e.message, type: "error" }); }
        finally { setBusy(null); }
    }

    if (loading) return <div className="text-center py-12 text-gray-500">Loading…</div>;

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">🗂️ My Plans</h1>
                    <p className="text-gray-500 mt-1">Each plan bundles a milestone, daily goals, nutrition requirement and meal setting. Activate one as a whole.</p>
                </div>
                <a href="/plan-setup" className="shrink-0 px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700">✨ Build with AI</a>
            </div>

            {message && (
                <div className={`px-4 py-3 rounded-xl border text-sm ${message.type === "success" ? "bg-green-50 text-green-800 border-green-200" : "bg-red-50 text-red-800 border-red-200"}`}>{message.text}</div>
            )}

            {plans.length === 0 ? (
                <div className="text-center py-16 bg-gray-50 rounded-2xl border border-dashed border-gray-300">
                    <p className="text-gray-600 font-medium">No plans yet.</p>
                    <a href="/plan-setup" className="inline-block mt-3 px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700">Build one with AI</a>
                </div>
            ) : plans.map((p) => (
                <div key={p.id} className={`bg-white rounded-2xl shadow-sm border p-5 space-y-4 ${p.active ? "border-green-300" : "border-gray-100"}`}>
                    <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-2 flex-wrap">
                            <h2 className="text-lg font-bold text-gray-900">{p.name}</h2>
                            <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${SOURCE_BADGE[p.source]?.cls || "bg-gray-100 text-gray-600"}`}>{SOURCE_BADGE[p.source]?.label || p.source}</span>
                            {p.active && <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-green-100 text-green-700">Active</span>}
                        </div>
                        <div className="flex gap-2 shrink-0">
                            {p.active
                                ? <button onClick={() => act(p, "deactivate")} disabled={busy === p.id} className="text-xs px-3 py-1.5 rounded-lg font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-50">Deactivate</button>
                                : <button onClick={() => act(p, "activate")} disabled={busy === p.id} className="text-xs px-3 py-1.5 rounded-lg font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50">Activate</button>}
                            <button onClick={() => act(p, "delete")} disabled={busy === p.id} className="text-xs px-3 py-1.5 rounded-lg font-medium bg-white border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50">Delete</button>
                        </div>
                    </div>

                    {p.missing.length > 0 && (
                        <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 flex items-center justify-between gap-2">
                            <span>Missing: {p.missing.map((m) => MISSING_LABEL[m] || m).join(", ")}</span>
                            <a href="/plan-setup" className="font-semibold text-indigo-700 hover:underline whitespace-nowrap">Complete →</a>
                        </div>
                    )}

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                        <div className="rounded-xl border border-gray-100 p-3">
                            <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Milestone</p>
                            {p.milestone ? (
                                <p className="text-gray-700">{p.milestone.name || (p.milestone.milestone_type || "").replace(/_/g, " ")}
                                    <span className="text-gray-400"> · {p.milestone.target_weight ? `${p.milestone.target_weight} kg` : p.milestone.target_value ? `${p.milestone.target_value} ${p.milestone.unit || ""}` : ""}{p.milestone.duration_days ? ` · ${p.milestone.duration_days}d` : ""}</span>
                                </p>
                            ) : <p className="text-gray-300 italic">none</p>}
                        </div>
                        <div className="rounded-xl border border-gray-100 p-3">
                            <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Nutrition</p>
                            {p.nutrition_target ? (
                                <p className="text-gray-700">{p.nutrition_target.calories_kcal} kcal <span className="text-gray-400">· P{Math.round(p.nutrition_target.protein_g)} C{Math.round(p.nutrition_target.carbs_g)} F{Math.round(p.nutrition_target.fat_g)}</span></p>
                            ) : <p className="text-gray-300 italic">none</p>}
                        </div>
                        <div className="rounded-xl border border-gray-100 p-3">
                            <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Meal setting</p>
                            {p.meal_setting ? (
                                <p className="text-gray-700">{p.meal_setting.name} <span className="text-gray-400">· {p.meal_setting.timed_meals_per_day} meals</span></p>
                            ) : <p className="text-gray-300 italic">none</p>}
                        </div>
                        <div className="rounded-xl border border-gray-100 p-3">
                            <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1">Daily goals ({p.daily_goals.length})</p>
                            {p.daily_goals.length ? (
                                <p className="text-gray-700 line-clamp-2">{p.daily_goals.map((d) => d.name).join(", ")}</p>
                            ) : <p className="text-gray-300 italic">none</p>}
                        </div>
                    </div>

                    <div className="flex gap-3 text-xs text-gray-500 pt-1">
                        <a href="/goal" className="hover:underline">Edit milestone</a>
                        <a href="/nutrition" className="hover:underline">Edit nutrition</a>
                        <a href="/meal-settings" className="hover:underline">Edit meals</a>
                        <a href="/daily-goals" className="hover:underline">Edit daily goals</a>
                    </div>
                </div>
            ))}
        </div>
    );
}
