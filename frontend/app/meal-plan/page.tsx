"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { NutritionTargetRead } from "@/lib/types";

// ── Types ──────────────────────────────────────────────────────────────────
type MealIngredient = {
    food_item_name: string;
    quantity: number;
    unit: string;
};

type FullMealDetails = {
    id: string;
    name: string;
    description: string | null;
    instructions: string | null;
    image_url: string | null;
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
    servings: number;
    total_weight_g: number | null;
    labels: string[];
    ingredients: MealIngredient[];
};

type ComboMeal = {
    meal_id: string;
    meal_name: string;
    meal_image_url: string | null;
    servings: number;
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
};

type ComboOption = {
    option_id: string;
    combo_id: string;
    combo_name: string;
    rank: number;
    is_chosen: boolean;
    macros: { calories: number; protein_g: number; carbs_g: number; fat_g: number };
    meals: ComboMeal[];
};

type TimedMealData = {
    timed_meal_id: string;
    meal_time: string;
    macros: { calories: number; protein_g: number; carbs_g: number; fat_g: number };
    combo_options: ComboOption[];
};

type DayPlan = {
    day_plan_id: string;
    plan_date: string;
    timed_meals: TimedMealData[];
};

type WeekPlan = {
    week_plan_id: string;
    title: string;
    start_date: string;
    end_date: string;
    status: string;
    days: DayPlan[];
};

// ── Color map for meal times ───────────────────────────────────────────────
const mealTimeColors: Record<string, { bg: string; text: string; icon: string }> = {
    breakfast: { bg: "bg-amber-50", text: "text-amber-700", icon: "🌅" },
    lunch: { bg: "bg-green-50", text: "text-green-700", icon: "☀️" },
    dinner: { bg: "bg-indigo-50", text: "text-indigo-700", icon: "🌙" },
    snack: { bg: "bg-pink-50", text: "text-pink-700", icon: "🍿" },
};

const getMealStyle = (mt: string) => mealTimeColors[mt] || { bg: "bg-gray-50", text: "text-gray-700", icon: "🍽️" };

// ── Main Page ──────────────────────────────────────────────────────────────
export default function MealPlanPage() {
    const [plans, setPlans] = useState<WeekPlan[]>([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState<string | null>(null); // "day" | "week" | timed_meal_id
    const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
    const [expandedDay, setExpandedDay] = useState<string | null>(null);
    const [expandedTimedMeal, setExpandedTimedMeal] = useState<string | null>(null);
    const [nutritionTarget, setNutritionTarget] = useState<NutritionTargetRead | null>(null);

    // Meal Modal State
    const [expandedMealDetails, setExpandedMealDetails] = useState<FullMealDetails | null>(null);
    const [loadingMealDetails, setLoadingMealDetails] = useState(false);

    // Day of week selector
    const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] as const;
    const todayIdx = (new Date().getDay() + 6) % 7; // 0=Mon
    const [selectedDayIdx, setSelectedDayIdx] = useState(todayIdx);

    const getDateForDayIdx = (idx: number) => {
        const today = new Date();
        const currentIdx = (today.getDay() + 6) % 7; // 0=Mon
        let diff = idx - currentIdx;
        if (diff < 0) diff += 7;
        const target = new Date(today);
        target.setDate(today.getDate() + diff);
        return target.toISOString().split("T")[0];
    };

    const getWeekStartDate = () => {
        const today = new Date();
        const currentIdx = (today.getDay() + 6) % 7;
        const monday = new Date(today);
        monday.setDate(today.getDate() - currentIdx);
        return monday.toISOString().split("T")[0];
    };

    useEffect(() => {
        loadPlans();
    }, []);

    async function loadPlans() {
        try {
            const [data, targetData] = await Promise.all([
                apiFetch<WeekPlan[]>("/api/meal-plans/me"),
                apiFetch<NutritionTargetRead>("/api/nutrition-target/me").catch(() => null)
            ]);

            setPlans(data);
            setNutritionTarget(targetData);
            if (data.length > 0 && data[0].days.length > 0 && !expandedDay) {
                setExpandedDay(data[0].days[0].day_plan_id);
            }
        } catch (err: any) {
            console.error("Failed to load plans:", err);
        } finally {
            setLoading(false);
        }
    }

    async function handleGenerateDay() {
        setGenerating("day");
        setMessage(null);
        try {
            const planDate = getDateForDayIdx(selectedDayIdx);
            await apiFetch("/api/meal-plans/generate-day", {
                method: "POST",
                body: { plan_date: planDate },
            });
            setMessage({ text: `${DAYS[selectedDayIdx]} plan generated! 🎉`, type: "success" });
            await loadPlans();
        } catch (err: any) {
            setMessage({ text: `Failed: ${err.message}`, type: "error" });
        } finally {
            setGenerating(null);
        }
    }

    async function handleGenerateWeek() {
        setGenerating("week");
        setMessage(null);
        try {
            await apiFetch("/api/meal-plans/generate-week", {
                method: "POST",
                body: { start_date: getWeekStartDate() },
            });
            setMessage({ text: "Week plan generated! 🎉", type: "success" });
            await loadPlans();
        } catch (err: any) {
            setMessage({ text: `Failed: ${err.message}`, type: "error" });
        } finally {
            setGenerating(null);
        }
    }

    async function handleRegenerateTimedMeal(timedMealId: string) {
        setGenerating(timedMealId);
        setMessage(null);
        try {
            await apiFetch(`/api/meal-plans/timed-meal/${timedMealId}/regenerate`, {
                method: "POST",
            });
            setMessage({ text: "Timed meal regenerated! 🔄", type: "success" });
            await loadPlans();
        } catch (err: any) {
            setMessage({ text: `Regeneration failed: ${err.message}`, type: "error" });
        } finally {
            setGenerating(null);
        }
    }

    async function handleSwap(timedMealId: string, optionId: string) {
        setMessage(null);
        try {
            await apiFetch(`/api/meal-plans/timed-meal/${timedMealId}/swap`, {
                method: "PATCH",
                body: { combo_option_id: optionId },
            });
            setMessage({ text: "Combo swapped! ✅", type: "success" });
            await loadPlans();
        } catch (err: any) {
            setMessage({ text: `Swap failed: ${err.message}`, type: "error" });
        }
    }

    async function handleMealClick(mealId: string) {
        setLoadingMealDetails(true);
        try {
            const data = await apiFetch<FullMealDetails>(`/api/meals/${mealId}`);
            setExpandedMealDetails(data);
        } catch (err) {
            console.error("Failed to load meal details", err);
        } finally {
            setLoadingMealDetails(false);
        }
    }

    async function handleDeleteDay(dayPlanId: string) {
        if (!confirm("Delete this day plan? This cannot be undone.")) return;
        setGenerating(`del-day-${dayPlanId}`);
        setMessage(null);
        try {
            await apiFetch(`/api/meal-plans/day-plan/${dayPlanId}`, { method: "DELETE" });
            setMessage({ text: "Day plan deleted.", type: "success" });
            await loadPlans();
        } catch (err: any) {
            setMessage({ text: `Delete failed: ${err.message}`, type: "error" });
        } finally {
            setGenerating(null);
        }
    }

    async function handleRegenerateDay(dayPlanId: string, label: string) {
        if (!confirm(`Regenerate the plan for ${label}? The current plan will be replaced.`)) return;
        setGenerating(`regen-day-${dayPlanId}`);
        setMessage(null);
        try {
            await apiFetch(`/api/meal-plans/day-plan/${dayPlanId}/regenerate`, { method: "POST" });
            setMessage({ text: `${label} plan regenerated! 🔄`, type: "success" });
            await loadPlans();
        } catch (err: any) {
            setMessage({ text: `Regeneration failed: ${err.message}`, type: "error" });
        } finally {
            setGenerating(null);
        }
    }

    async function handleDeleteWeek(weekPlanId: string) {
        if (!confirm("Delete this entire week plan? This cannot be undone.")) return;
        setGenerating(`del-week-${weekPlanId}`);
        setMessage(null);
        try {
            await apiFetch(`/api/meal-plans/week-plan/${weekPlanId}`, { method: "DELETE" });
            setMessage({ text: "Week plan deleted.", type: "success" });
            await loadPlans();
        } catch (err: any) {
            setMessage({ text: `Delete failed: ${err.message}`, type: "error" });
        } finally {
            setGenerating(null);
        }
    }

    async function handleRegenerateWeek(weekPlanId: string) {
        if (!confirm("Regenerate this entire week plan? All current plans will be replaced.")) return;
        setGenerating(`regen-week-${weekPlanId}`);
        setMessage(null);
        try {
            await apiFetch(`/api/meal-plans/week-plan/${weekPlanId}/regenerate`, { method: "POST" });
            setMessage({ text: "Week plan regenerated! 🔄", type: "success" });
            await loadPlans();
        } catch (err: any) {
            setMessage({ text: `Regeneration failed: ${err.message}`, type: "error" });
        } finally {
            setGenerating(null);
        }
    }

    // ── UI ──────────────────────────────────────────────────────────────────
    if (loading) {
        return (
            <div className="flex justify-center items-center py-24">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
            </div>
        );
    }

    return (
        <div className="max-w-5xl mx-auto p-4 md:p-8 space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-gray-900">🍱 Meal Plans</h1>
                <p className="text-gray-500 mt-1">
                    AI-powered meal plans tailored to your nutrition targets and preferences.
                </p>
            </div>

            {/* Generate Controls */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4">

                {/* Day of Week Selector */}
                <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                        Select Day
                    </label>
                    <div className="flex gap-1.5 flex-wrap">
                        {DAYS.map((day, idx) => (
                            <button
                                key={day}
                                onClick={() => setSelectedDayIdx(idx)}
                                className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${selectedDayIdx === idx
                                    ? "bg-orange-500 text-white shadow-md"
                                    : idx === todayIdx
                                        ? "bg-orange-50 text-orange-700 border border-orange-200 hover:bg-orange-100"
                                        : "bg-gray-50 text-gray-600 border border-gray-200 hover:bg-gray-100"
                                    }`}
                            >
                                {day.slice(0, 3)}
                                {idx === todayIdx && selectedDayIdx !== idx && (
                                    <span className="ml-1 text-[10px] opacity-70">Today</span>
                                )}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-1">
                    <button
                        onClick={handleGenerateDay}
                        disabled={generating !== null}
                        className="px-5 py-2.5 bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-xl shadow-md hover:shadow-lg transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    >
                        {generating === "day" ? (
                            <span className="flex items-center gap-2">
                                <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
                                Generating...
                            </span>
                        ) : (
                            `📅 Generate ${DAYS[selectedDayIdx]}`
                        )}
                    </button>
                    <button
                        onClick={handleGenerateWeek}
                        disabled={generating !== null}
                        className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-md hover:shadow-lg transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    >
                        {generating === "week" ? (
                            <span className="flex items-center gap-2">
                                <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
                                Generating...
                            </span>
                        ) : (
                            "📆 Generate Full Week"
                        )}
                    </button>
                </div>
            </div>

            {/* Message */}
            {message && (
                <div
                    className={`px-4 py-3 rounded-xl border text-sm font-medium ${message.type === "success"
                        ? "bg-green-50 text-green-800 border-green-200"
                        : "bg-red-50 text-red-800 border-red-200"
                        }`}
                >
                    {message.text}
                </div>
            )}

            {/* Empty State */}
            {plans.length === 0 && (
                <div className="text-center py-20 bg-gray-50 rounded-2xl border border-dashed border-gray-300">
                    <span className="text-5xl block mb-4">🥗</span>
                    <h2 className="text-xl font-semibold text-gray-700 mb-2">No Meal Plans Yet</h2>
                    <p className="text-gray-500 max-w-md mx-auto">
                        Make sure you have an active <strong>Meal Plan Setting</strong> and <strong>Nutrition Target</strong>,
                        then click "Generate Day" or "Generate Week" to create your personalized plan.
                    </p>
                </div>
            )}

            {/* Plans */}
            {plans.map((wp) => (
                <div key={wp.week_plan_id} className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                    {/* Week Header */}
                    <div className="bg-gradient-to-r from-orange-500 to-amber-500 px-6 py-4 text-white">
                        <div className="flex justify-between items-center">
                            <div>
                                <h2 className="text-lg font-bold">{wp.title}</h2>
                                <p className="text-orange-100 text-sm">
                                    {wp.start_date} → {wp.end_date} • {wp.status}
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-xs bg-white/20 px-3 py-1 rounded-full font-medium">
                                    {wp.days.length} days
                                </span>
                                <button
                                    onClick={() => handleRegenerateWeek(wp.week_plan_id)}
                                    disabled={generating !== null}
                                    title="Regenerate entire week plan"
                                    className="text-xs px-3 py-1.5 bg-white/20 hover:bg-white/30 rounded-lg font-medium disabled:opacity-50 transition-colors"
                                >
                                    {generating === `regen-week-${wp.week_plan_id}` ? (
                                        <span className="flex items-center gap-1"><span className="animate-spin inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full"></span> Regenerating...</span>
                                    ) : "🔄 Regenerate Week"}
                                </button>
                                <button
                                    onClick={() => handleDeleteWeek(wp.week_plan_id)}
                                    disabled={generating !== null}
                                    title="Delete entire week plan"
                                    className="text-xs px-3 py-1.5 bg-red-500/80 hover:bg-red-600/90 rounded-lg font-medium disabled:opacity-50 transition-colors"
                                >
                                    {generating === `del-week-${wp.week_plan_id}` ? "Deleting..." : "🗑️ Delete Week"}
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Days */}
                    <div className="divide-y divide-gray-100">
                        {wp.days.map((day) => {
                            const isExpanded = expandedDay === day.day_plan_id;
                            const dayName = new Date(day.plan_date + "T00:00:00").toLocaleDateString("en-US", {
                                weekday: "long",
                                month: "short",
                                day: "numeric",
                            });

                            // Calculate day totals from chosen combos
                            const dayTotals = day.timed_meals.reduce(
                                (acc, tm) => ({
                                    calories: acc.calories + (tm.macros?.calories || 0),
                                    protein: acc.protein + (tm.macros?.protein_g || 0),
                                    carbs: acc.carbs + (tm.macros?.carbs_g || 0),
                                    fat: acc.fat + (tm.macros?.fat_g || 0),
                                }),
                                { calories: 0, protein: 0, carbs: 0, fat: 0 }
                            );

                            return (
                                <div key={day.day_plan_id}>
                                    {/* Day Header (collapsible) */}
                                    <div className="w-full px-6 py-4 flex justify-between items-center hover:bg-gray-50 transition-colors">
                                        <button
                                            onClick={() => setExpandedDay(isExpanded ? null : day.day_plan_id)}
                                            className="flex items-center gap-3 flex-1 text-left"
                                        >
                                            <span className="text-lg">{isExpanded ? "📖" : "📋"}</span>
                                            <div>
                                                <p className="font-semibold text-gray-900">{dayName}</p>
                                                <p className="text-xs text-gray-500">
                                                    {day.timed_meals.length} meals •{" "}
                                                    {Math.round(dayTotals.calories)} kcal •{" "}
                                                    P:{Math.round(dayTotals.protein)}g •{" "}
                                                    C:{Math.round(dayTotals.carbs)}g •{" "}
                                                    F:{Math.round(dayTotals.fat)}g
                                                </p>
                                            </div>
                                        </button>
                                        <div className="flex items-center gap-2 ml-3">
                                            <button
                                                onClick={() => handleRegenerateDay(day.day_plan_id, dayName)}
                                                disabled={generating !== null}
                                                title="Regenerate this day's plan"
                                                className="text-xs px-2.5 py-1.5 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg hover:bg-indigo-100 font-medium disabled:opacity-50 transition-colors"
                                            >
                                                {generating === `regen-day-${day.day_plan_id}` ? "⏳" : "🔄"}
                                            </button>
                                            <button
                                                onClick={() => handleDeleteDay(day.day_plan_id)}
                                                disabled={generating !== null}
                                                title="Delete this day's plan"
                                                className="text-xs px-2.5 py-1.5 bg-red-50 text-red-600 border border-red-200 rounded-lg hover:bg-red-100 font-medium disabled:opacity-50 transition-colors"
                                            >
                                                {generating === `del-day-${day.day_plan_id}` ? "⏳" : "🗑️"}
                                            </button>
                                            <span className="text-gray-400 text-sm">{isExpanded ? "▲" : "▼"}</span>
                                        </div>
                                    </div>

                                    {/* Expanded Day Content */}
                                    {isExpanded && (
                                        <div className="px-6 pb-6 space-y-6">
                                            {/* Daily Nutrition Summary */}
                                            <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm mb-4">
                                                <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                                    📊 Daily Nutrition Overview
                                                </h3>
                                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                                    <div className="bg-gray-50 rounded-lg p-3">
                                                        <p className="text-xs text-gray-500 font-medium mb-1">Calories</p>
                                                        <div className="flex items-end gap-2">
                                                            <span className="text-lg font-bold text-gray-900">{Math.round(dayTotals.calories)}</span>
                                                            {nutritionTarget && (
                                                                <span className="text-xs text-gray-400 mb-1">/ {nutritionTarget.calories_kcal} kcal</span>
                                                            )}
                                                        </div>
                                                        {nutritionTarget && (
                                                            <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
                                                                <div className="bg-orange-500 h-1.5 rounded-full" style={{ width: `${Math.min(100, (dayTotals.calories / nutritionTarget.calories_kcal) * 100)}%` }}></div>
                                                            </div>
                                                        )}
                                                    </div>
                                                    <div className="bg-gray-50 rounded-lg p-3">
                                                        <p className="text-xs text-gray-500 font-medium mb-1">Protein</p>
                                                        <div className="flex items-end gap-2">
                                                            <span className="text-lg font-bold text-blue-700">{Math.round(dayTotals.protein)}g</span>
                                                            {nutritionTarget && (
                                                                <span className="text-xs text-gray-400 mb-1">/ {nutritionTarget.protein_g}g</span>
                                                            )}
                                                        </div>
                                                        {nutritionTarget && (
                                                            <div className="w-full bg-blue-100 rounded-full h-1.5 mt-2">
                                                                <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${Math.min(100, (dayTotals.protein / nutritionTarget.protein_g) * 100)}%` }}></div>
                                                            </div>
                                                        )}
                                                    </div>
                                                    <div className="bg-gray-50 rounded-lg p-3">
                                                        <p className="text-xs text-gray-500 font-medium mb-1">Carbs</p>
                                                        <div className="flex items-end gap-2">
                                                            <span className="text-lg font-bold text-green-700">{Math.round(dayTotals.carbs)}g</span>
                                                            {nutritionTarget && (
                                                                <span className="text-xs text-gray-400 mb-1">/ {nutritionTarget.carbs_g}g</span>
                                                            )}
                                                        </div>
                                                        {nutritionTarget && (
                                                            <div className="w-full bg-green-100 rounded-full h-1.5 mt-2">
                                                                <div className="bg-green-500 h-1.5 rounded-full" style={{ width: `${Math.min(100, (dayTotals.carbs / nutritionTarget.carbs_g) * 100)}%` }}></div>
                                                            </div>
                                                        )}
                                                    </div>
                                                    <div className="bg-gray-50 rounded-lg p-3">
                                                        <p className="text-xs text-gray-500 font-medium mb-1">Fat</p>
                                                        <div className="flex items-end gap-2">
                                                            <span className="text-lg font-bold text-red-700">{Math.round(dayTotals.fat)}g</span>
                                                            {nutritionTarget && (
                                                                <span className="text-xs text-gray-400 mb-1">/ {nutritionTarget.fat_g}g</span>
                                                            )}
                                                        </div>
                                                        {nutritionTarget && (
                                                            <div className="w-full bg-red-100 rounded-full h-1.5 mt-2">
                                                                <div className="bg-red-500 h-1.5 rounded-full" style={{ width: `${Math.min(100, (dayTotals.fat / nutritionTarget.fat_g) * 100)}%` }}></div>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Timed Meals */}
                                            <div className="space-y-4">
                                                {day.timed_meals.map((tm) => {
                                                    const style = getMealStyle(tm.meal_time);
                                                    const chosen = tm.combo_options.find((o) => o.is_chosen);
                                                    const isTimedExpanded = expandedTimedMeal === tm.timed_meal_id;

                                                    return (
                                                        <div
                                                            key={tm.timed_meal_id}
                                                            className={`${style.bg} rounded-xl border border-gray-200 overflow-hidden`}
                                                        >
                                                            {/* Timed Meal Header */}
                                                            <div className="px-4 py-3 flex justify-between items-center">
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-xl">{style.icon}</span>
                                                                    <div>
                                                                        <h3
                                                                            className={`font-bold capitalize ${style.text}`}
                                                                        >
                                                                            {tm.meal_time.replace("_", " ")}
                                                                        </h3>
                                                                        {chosen && (
                                                                            <p className="text-xs text-gray-500">
                                                                                {Math.round(chosen.macros.calories)} kcal •{" "}
                                                                                P:{Math.round(chosen.macros.protein_g)}g •{" "}
                                                                                C:{Math.round(chosen.macros.carbs_g)}g •{" "}
                                                                                F:{Math.round(chosen.macros.fat_g)}g
                                                                            </p>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                                <div className="flex items-center gap-2">
                                                                    <button
                                                                        onClick={() =>
                                                                            handleRegenerateTimedMeal(tm.timed_meal_id)
                                                                        }
                                                                        disabled={generating !== null}
                                                                        className="text-xs px-3 py-1.5 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 font-medium text-gray-600 disabled:opacity-50"
                                                                    >
                                                                        {generating === tm.timed_meal_id
                                                                            ? "⏳"
                                                                            : "🔄 Regenerate"}
                                                                    </button>
                                                                    <button
                                                                        onClick={() =>
                                                                            setExpandedTimedMeal(
                                                                                isTimedExpanded ? null : tm.timed_meal_id
                                                                            )
                                                                        }
                                                                        className="text-xs px-3 py-1.5 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 font-medium text-gray-600"
                                                                    >
                                                                        {isTimedExpanded
                                                                            ? "Hide Options"
                                                                            : `View ${tm.combo_options.length} Options`}
                                                                    </button>
                                                                </div>
                                                            </div>

                                                            {/* Chosen Combo Full Meal Cards Setup */}
                                                            {chosen && !isTimedExpanded && (
                                                                <div className="px-4 pb-4">
                                                                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                                                        {chosen.meals.map((m, i) => (
                                                                            <div
                                                                                key={i}
                                                                                onClick={() => handleMealClick(m.meal_id)}
                                                                                className="flex flex-col bg-white rounded-xl overflow-hidden border border-gray-200 shadow-sm transition-shadow hover:shadow-md cursor-pointer relative"
                                                                            >
                                                                                {loadingMealDetails && (
                                                                                    <div className="absolute inset-x-0 top-0 h-1 bg-orange-100 overflow-hidden z-10">
                                                                                        <div className="h-full bg-orange-500 w-1/3 animate-[slide_1s_ease-in-out_infinite]"></div>
                                                                                    </div>
                                                                                )}
                                                                                {/* Image filling top half */}
                                                                                <div className="h-32 w-full bg-gray-100 relative group overflow-hidden">
                                                                                    {m.meal_image_url ? (
                                                                                        <img
                                                                                            src={m.meal_image_url}
                                                                                            alt={m.meal_name}
                                                                                            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                                                                                        />
                                                                                    ) : (
                                                                                        <div className="w-full h-full flex flex-col items-center justify-center text-gray-400">
                                                                                            <span className="text-3xl mb-1">🍽️</span>
                                                                                            <span className="text-xs font-medium">No Image</span>
                                                                                        </div>
                                                                                    )}
                                                                                    <div className="absolute top-2 right-2 bg-white/90 backdrop-blur-sm px-2 py-1 rounded-md shadow-sm border border-white/20">
                                                                                        <p className="text-xs font-bold text-gray-800">×{m.servings} <span className="text-[10px] text-gray-500 font-medium">srv</span></p>
                                                                                    </div>
                                                                                </div>

                                                                                {/* Meal Details below */}
                                                                                <div className="p-3">
                                                                                    <h4 className="font-bold text-gray-900 leading-tight mb-2 line-clamp-2" title={m.meal_name}>
                                                                                        {m.meal_name}
                                                                                    </h4>

                                                                                    {/* Macros grid inside card */}
                                                                                    <div className="grid grid-cols-4 gap-1 text-center bg-gray-50 rounded-lg p-1.5">
                                                                                        <div>
                                                                                            <p className="text-[11px] font-bold text-gray-800">{Math.round(m.calories)}</p>
                                                                                            <p className="text-[8px] uppercase tracking-wider text-gray-500">kcal</p>
                                                                                        </div>
                                                                                        <div>
                                                                                            <p className="text-[11px] font-bold text-blue-600">{Math.round(m.protein_g)}g</p>
                                                                                            <p className="text-[8px] uppercase tracking-wider text-blue-400">Pro</p>
                                                                                        </div>
                                                                                        <div>
                                                                                            <p className="text-[11px] font-bold text-green-600">{Math.round(m.carbs_g)}g</p>
                                                                                            <p className="text-[8px] uppercase tracking-wider text-green-400">Carb</p>
                                                                                        </div>
                                                                                        <div>
                                                                                            <p className="text-[11px] font-bold text-red-600">{Math.round(m.fat_g)}g</p>
                                                                                            <p className="text-[8px] uppercase tracking-wider text-red-400">Fat</p>
                                                                                        </div>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        ))}
                                                                    </div>
                                                                </div>
                                                            )}

                                                            {/* All Combo Options */}
                                                            {isTimedExpanded && (
                                                                <div className="px-4 pb-4 space-y-2">
                                                                    {tm.combo_options
                                                                        .sort((a, b) => a.rank - b.rank)
                                                                        .map((opt) => (
                                                                            <div
                                                                                key={opt.option_id}
                                                                                className={`rounded-xl border-2 p-3 transition-all ${opt.is_chosen
                                                                                    ? "border-orange-400 bg-white shadow-md"
                                                                                    : "border-gray-200 bg-white/60 hover:bg-white hover:border-gray-300"
                                                                                    }`}
                                                                            >
                                                                                <div className="flex justify-between items-start mb-2">
                                                                                    <div className="flex items-center gap-2">
                                                                                        <span
                                                                                            className={`text-xs font-bold px-2 py-0.5 rounded-full ${opt.is_chosen
                                                                                                ? "bg-orange-100 text-orange-700"
                                                                                                : "bg-gray-100 text-gray-600"
                                                                                                }`}
                                                                                        >
                                                                                            #{opt.rank}
                                                                                        </span>
                                                                                        {opt.is_chosen && (
                                                                                            <span className="text-xs text-orange-600 font-semibold">
                                                                                                ✅ Chosen
                                                                                            </span>
                                                                                        )}
                                                                                    </div>
                                                                                    {!opt.is_chosen && (
                                                                                        <button
                                                                                            onClick={() =>
                                                                                                handleSwap(
                                                                                                    tm.timed_meal_id,
                                                                                                    opt.option_id
                                                                                                )
                                                                                            }
                                                                                            className="text-xs px-3 py-1 bg-orange-500 text-white rounded-lg hover:bg-orange-600 font-medium transition-colors"
                                                                                        >
                                                                                            Choose This
                                                                                        </button>
                                                                                    )}
                                                                                </div>

                                                                                {/* Meals in option */}
                                                                                <div className="flex gap-2 flex-wrap mb-2">
                                                                                    {opt.meals.map((m, i) => (
                                                                                        <div
                                                                                            key={i}
                                                                                            className="flex items-center gap-2 bg-gray-50 rounded-lg px-2.5 py-1.5 border border-gray-100"
                                                                                        >
                                                                                            {m.meal_image_url ? (
                                                                                                <img
                                                                                                    src={m.meal_image_url}
                                                                                                    alt={m.meal_name}
                                                                                                    className="w-7 h-7 rounded object-cover"
                                                                                                />
                                                                                            ) : (
                                                                                                <div className="w-7 h-7 rounded bg-gray-200 flex items-center justify-center text-[10px]">
                                                                                                    🍽️
                                                                                                </div>
                                                                                            )}
                                                                                            <div>
                                                                                                <p className="text-xs font-medium text-gray-800 leading-tight">
                                                                                                    {m.meal_name}
                                                                                                </p>
                                                                                                <p className="text-[10px] text-gray-400">
                                                                                                    ×{m.servings} •{" "}
                                                                                                    {Math.round(m.calories)}{" "}
                                                                                                    kcal
                                                                                                </p>
                                                                                            </div>
                                                                                        </div>
                                                                                    ))}
                                                                                </div>

                                                                                {/* Macros bar */}
                                                                                <div className="grid grid-cols-4 gap-1 text-center">
                                                                                    <div className="bg-gray-50 rounded-md py-1">
                                                                                        <p className="text-xs font-bold text-gray-800">
                                                                                            {Math.round(opt.macros.calories)}
                                                                                        </p>
                                                                                        <p className="text-[9px] text-gray-500">
                                                                                            kcal
                                                                                        </p>
                                                                                    </div>
                                                                                    <div className="bg-blue-50 rounded-md py-1">
                                                                                        <p className="text-xs font-bold text-blue-700">
                                                                                            {Math.round(
                                                                                                opt.macros.protein_g
                                                                                            )}
                                                                                            g
                                                                                        </p>
                                                                                        <p className="text-[9px] text-blue-500">
                                                                                            Protein
                                                                                        </p>
                                                                                    </div>
                                                                                    <div className="bg-green-50 rounded-md py-1">
                                                                                        <p className="text-xs font-bold text-green-700">
                                                                                            {Math.round(
                                                                                                opt.macros.carbs_g
                                                                                            )}
                                                                                            g
                                                                                        </p>
                                                                                        <p className="text-[9px] text-green-500">
                                                                                            Carbs
                                                                                        </p>
                                                                                    </div>
                                                                                    <div className="bg-red-50 rounded-md py-1">
                                                                                        <p className="text-xs font-bold text-red-700">
                                                                                            {Math.round(opt.macros.fat_g)}g
                                                                                        </p>
                                                                                        <p className="text-[9px] text-red-500">
                                                                                            Fat
                                                                                        </p>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        ))}
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            ))}

            {/* Meal Details Modal */}
            {expandedMealDetails && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300"
                    onClick={() => setExpandedMealDetails(null)}
                >
                    <div
                        className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto"
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Header Image */}
                        <div className="relative h-64 sm:h-80 bg-gray-100 flex-shrink-0">
                            {expandedMealDetails.image_url ? (
                                <img src={expandedMealDetails.image_url} alt={expandedMealDetails.name} className="w-full h-full object-cover" />
                            ) : (
                                <div className="absolute inset-0 flex items-center justify-center text-6xl opacity-20">🍽️</div>
                            )}
                            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"></div>

                            <button
                                onClick={() => setExpandedMealDetails(null)}
                                className="absolute top-4 left-4 p-2 bg-black/40 text-white rounded-full hover:bg-black/60 transition-all backdrop-blur-md"
                            >
                                ✕
                            </button>

                            <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-8 text-white">
                                {expandedMealDetails.labels && expandedMealDetails.labels.length > 0 && (
                                    <div className="flex flex-wrap gap-2 mb-3">
                                        {expandedMealDetails.labels.map(l => (
                                            <span key={l} className="px-3 py-1 bg-white/20 backdrop-blur-sm text-white text-xs font-bold uppercase tracking-wider rounded-full shadow-sm border border-white/30">
                                                {l.replace('_', ' ')}
                                            </span>
                                        ))}
                                    </div>
                                )}
                                <h2 className="text-3xl sm:text-4xl font-extrabold leading-tight text-shadow-sm">{expandedMealDetails.name}</h2>
                                <p className="text-gray-200 mt-2 font-medium">{expandedMealDetails.servings} serving{expandedMealDetails.servings > 1 ? 's' : ''}</p>
                            </div>
                        </div>

                        {/* Modal Body */}
                        <div className="p-6 sm:p-8">
                            <div className="flex flex-col md:flex-row gap-8">
                                {/* Left Col: Details & Macros */}
                                <div className="flex-1 space-y-6">
                                    {expandedMealDetails.description && (
                                        <div>
                                            <h3 className="text-lg font-bold text-gray-800 mb-2">About this meal</h3>
                                            <p className="text-gray-600 leading-relaxed">{expandedMealDetails.description}</p>
                                        </div>
                                    )}

                                    <div className="bg-orange-50/50 border border-orange-100 rounded-xl p-5">
                                        <h3 className="text-sm font-bold text-orange-800 uppercase tracking-wider mb-4 flex items-center gap-2">
                                            <span>📊</span> Nutrition per serving
                                        </h3>
                                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                                            <div className="bg-white p-3 rounded-lg shadow-sm text-center border border-orange-100">
                                                <div className="text-2xl font-black text-gray-800">{expandedMealDetails.calories}</div>
                                                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mt-1">Calories</div>
                                            </div>
                                            <div className="bg-white p-3 rounded-lg shadow-sm text-center border border-indigo-50">
                                                <div className="text-2xl font-black text-indigo-600">{expandedMealDetails.protein_g}g</div>
                                                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mt-1">Protein</div>
                                            </div>
                                            <div className="bg-white p-3 rounded-lg shadow-sm text-center border border-emerald-50">
                                                <div className="text-2xl font-black text-emerald-600">{expandedMealDetails.carbs_g}g</div>
                                                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mt-1">Carbs</div>
                                            </div>
                                            <div className="bg-white p-3 rounded-lg shadow-sm text-center border border-rose-50">
                                                <div className="text-2xl font-black text-rose-500">{expandedMealDetails.fat_g}g</div>
                                                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mt-1">Fat</div>
                                            </div>
                                        </div>
                                    </div>

                                    {expandedMealDetails.instructions && (
                                        <div>
                                            <h3 className="text-lg font-bold text-gray-800 mb-3 flex items-center gap-2">
                                                <span>👨‍🍳</span> Preparation
                                            </h3>
                                            <div className="bg-gray-50 rounded-xl p-5 text-gray-700 whitespace-pre-wrap leading-relaxed text-sm">
                                                {expandedMealDetails.instructions}
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* Right Col: Ingredients */}
                                <div className="w-full md:w-72 flex-shrink-0">
                                    <div className="bg-gray-50 rounded-xl p-5 border border-gray-100 h-full">
                                        <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                                            <span>🧺</span> Ingredients
                                        </h3>
                                        {(!expandedMealDetails.ingredients || expandedMealDetails.ingredients.length === 0) ? (
                                            <p className="text-gray-400 text-sm italic">No ingredients listed.</p>
                                        ) : (
                                            <ul className="space-y-3">
                                                {expandedMealDetails.ingredients.map((ing, idx) => (
                                                    <li key={idx} className="flex justify-between items-start text-sm pb-3 border-b border-gray-200/60 last:border-0 last:pb-0">
                                                        <span className="font-semibold text-gray-700 pr-4">{ing.food_item_name}</span>
                                                        <span className="text-gray-500 whitespace-nowrap bg-white px-2 py-0.5 rounded shadow-sm border border-gray-100">
                                                            {ing.quantity} {ing.unit}
                                                        </span>
                                                    </li>
                                                ))}
                                            </ul>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
