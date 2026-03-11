"use client";

import { useEffect, useState, FormEvent } from "react";
import { apiFetch } from "@/lib/api";

type MealPlanSettingTimedMeal = {
    name: string;
    meal_time: string;
    calories_pct: number;
    protein_g_pct: number;
    carbs_g_pct: number;
    fat_g_pct: number;
    meal_labels: string[];
};

const ALL_MEAL_LABELS = [
    "breakfast", "lunch", "dinner", "snack",
    "main_meal", "side_meal", "drink", "dessert",
    "halal", "vegetarian", "vegan",
    "high_protein", "low_carb", "gym_friendly",
    "other",
];

type MealPlanSetting = {
    id: string;
    name: string;
    timed_meals_per_day: number;
    created_for: string;
    created_by: string;
    appointment_id: string | null;
    active: boolean;
    created_at: string;
    timed_meals: MealPlanSettingTimedMeal[];
    created_by_name?: string;
    created_by_email?: string;
};

export default function MealSettingsPage() {
    const [settings, setSettings] = useState<MealPlanSetting[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    // For creating a new custom setting
    const [newName, setNewName] = useState("My Custom Plan");
    const [timedMeals, setTimedMeals] = useState<MealPlanSettingTimedMeal[]>([
        { name: "Breakfast", meal_time: "breakfast", calories_pct: 35, protein_g_pct: 35, carbs_g_pct: 35, fat_g_pct: 35, meal_labels: ["breakfast"] },
        { name: "Lunch", meal_time: "lunch", calories_pct: 40, protein_g_pct: 40, carbs_g_pct: 40, fat_g_pct: 40, meal_labels: ["lunch", "main_meal"] },
        { name: "Dinner", meal_time: "dinner", calories_pct: 25, protein_g_pct: 25, carbs_g_pct: 25, fat_g_pct: 25, meal_labels: ["dinner", "main_meal"] },
    ]);

    useEffect(() => {
        loadSettings();
    }, []);

    async function loadSettings() {
        try {
            const data = await apiFetch<MealPlanSetting[]>("/api/meal-plan-settings/me");
            setSettings(data);
        } catch (error: any) {
            console.error("Failed to load settings:", error);
        } finally {
            setLoading(false);
        }
    }

    async function handleAdopt(id: string) {
        if (!confirm("Are you sure you want to adopt this meal plan setting? It will deactivate your current one.")) return;
        setSaving(true);
        setMessage(null);
        try {
            await apiFetch(`/api/meal-plan-settings/${id}/activate`, {
                method: "PATCH",
            });
            await loadSettings();
            setMessage("Meal Plan Setting adopted successfully.");
        } catch (e: any) {
            setMessage(`Failed to adopt: ${e.message}`);
        } finally {
            setSaving(false);
        }
    }

    async function handleCreate(e: FormEvent) {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        // Validate totals
        const totalCalories = timedMeals.reduce((acc, tm) => acc + tm.calories_pct, 0);
        const totalProtein = timedMeals.reduce((acc, tm) => acc + tm.protein_g_pct, 0);
        const totalCarbs = timedMeals.reduce((acc, tm) => acc + tm.carbs_g_pct, 0);
        const totalFat = timedMeals.reduce((acc, tm) => acc + tm.fat_g_pct, 0);

        if (totalCalories !== 100 || totalProtein !== 100 || totalCarbs !== 100 || totalFat !== 100) {
            setMessage("Error: All percentages (Calories, Protein, Carbs, Fat) must add up to exactly 100%.");
            setSaving(false);
            return;
        }

        try {
            await apiFetch("/api/meal-plan-settings/me", {
                method: "POST",
                body: {
                    name: newName,
                    timed_meals_per_day: timedMeals.length,
                    timed_meals: timedMeals
                },
            });
            await loadSettings();
            setMessage("New Meal Plan Setting created and activated.");
            setNewName("My Custom Plan");
            setTimedMeals([
                { name: "Breakfast", meal_time: "breakfast", calories_pct: 35, protein_g_pct: 35, carbs_g_pct: 35, fat_g_pct: 35, meal_labels: ["breakfast"] },
                { name: "Lunch", meal_time: "lunch", calories_pct: 40, protein_g_pct: 40, carbs_g_pct: 40, fat_g_pct: 40, meal_labels: ["lunch", "main_meal"] },
                { name: "Dinner", meal_time: "dinner", calories_pct: 25, protein_g_pct: 25, carbs_g_pct: 25, fat_g_pct: 25, meal_labels: ["dinner", "main_meal"] },
            ]);
        } catch (e: any) {
            setMessage(`Failed to create: ${e.message}`);
        } finally {
            setSaving(false);
        }
    }

    const activeSetting = settings.find((s) => s.active);
    const otherSettings = settings.filter((s) => !s.active);

    if (loading) {
        return <div className="p-8 text-center text-gray-500">Loading meal plan settings...</div>;
    }

    return (
        <div className="max-w-4xl mx-auto p-4 md:p-8">
            <h1 className="text-3xl font-bold mb-2">Meal Plan Settings</h1>
            <p className="text-gray-600 mb-8">
                Manage how your daily calories and macros are split across your meals.
            </p>

            {message && (
                <div className="mb-6 px-4 py-3 bg-blue-50 text-blue-800 rounded-xl border border-blue-200">
                    {message}
                </div>
            )}

            {/* Active Setting Section */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-8 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4">
                    <span className="bg-green-100 text-green-700 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                        Active
                    </span>
                </div>
                <h2 className="text-xl font-semibold mb-4 text-gray-800">Current Plan</h2>
                {activeSetting ? (
                    <div>
                        <div className="flex flex-wrap gap-4 mb-6">
                            <div>
                                <p className="text-sm text-gray-500 font-medium">Plan Name</p>
                                <p className="text-lg font-semibold">{activeSetting.name}</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-500 font-medium">Meals Per Day</p>
                                <p className="text-lg font-semibold">{activeSetting.timed_meals_per_day}</p>
                            </div>
                            {activeSetting.created_by !== activeSetting.created_for && (
                                <div>
                                    <p className="text-sm text-blue-500 font-medium">Suggested By Your Consultant</p>
                                    {activeSetting.created_by_name && (
                                        <div className="text-sm space-y-0.5 mt-0.5">
                                            <div className="font-semibold text-gray-800">👤 {activeSetting.created_by_name}</div>
                                            <div className="text-gray-500 text-xs">✉️ {activeSetting.created_by_email}</div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-3">Macro Distribution</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {activeSetting.timed_meals.map((tm, idx) => (
                                <div key={idx} className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                                    <h4 className="font-semibold text-gray-800 mb-2 capitalize">{tm.name} ({tm.meal_time.replace("_", " ")})</h4>
                                    <div className="space-y-1 text-sm">
                                        <div className="flex justify-between"><span className="text-gray-500">Calories:</span> <span className="font-medium text-gray-700">{tm.calories_pct}%</span></div>
                                        <div className="flex justify-between"><span className="text-gray-500">Protein:</span> <span className="font-medium text-gray-700">{tm.protein_g_pct}%</span></div>
                                        <div className="flex justify-between"><span className="text-gray-500">Carbs:</span> <span className="font-medium text-gray-700">{tm.carbs_g_pct}%</span></div>
                                        <div className="flex justify-between"><span className="text-gray-500">Fat:</span> <span className="font-medium text-gray-700">{tm.fat_g_pct}%</span></div>
                                    </div>
                                    {tm.meal_labels && tm.meal_labels.length > 0 && (
                                        <div className="mt-3 flex flex-wrap gap-1.5">
                                            {tm.meal_labels.map(lbl => (
                                                <span key={lbl} className="inline-block px-2 py-0.5 bg-blue-100 text-blue-700 text-[10px] rounded-full font-medium capitalize">{lbl.replace(/_/g, " ")}</span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                ) : (
                    <p className="text-gray-500">You don&apos;t have an active meal plan setting. Create or adopt one below.</p>
                )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                {/* Suggested / Previous Settings */}
                <div>
                    <h2 className="text-xl font-semibold mb-4 text-gray-800">Suggested & Past Plans</h2>
                    {otherSettings.length === 0 ? (
                        <p className="text-gray-500 text-sm italic">No other plans found.</p>
                    ) : (
                        <div className="space-y-4">
                            {otherSettings.map(setting => {
                                const isSuggestion = setting.created_by !== setting.created_for;
                                return (
                                    <div key={setting.id} className={`p-5 rounded-2xl border ${isSuggestion ? 'border-blue-200 bg-blue-50' : 'border-gray-200 bg-white'}`}>
                                        <div className="flex justify-between items-start mb-3">
                                            <div>
                                                {isSuggestion && <span className="text-xs font-bold text-blue-600 uppercase tracking-widest block mb-1">Consultant Suggestion</span>}
                                                {isSuggestion && setting.created_by_name && (
                                                    <div className="text-[11px] text-blue-700 mb-1 space-y-0.5">
                                                        <div>👤 <span className="font-medium">{setting.created_by_name}</span></div>
                                                        <div>✉️ <span>{setting.created_by_email}</span></div>
                                                    </div>
                                                )}
                                                <h3 className="font-semibold text-gray-900">{setting.name}</h3>
                                                <p className="text-xs text-gray-500">{setting.timed_meals_per_day} meals • Created {new Date(setting.created_at).toLocaleDateString()}</p>
                                            </div>
                                            <button
                                                onClick={() => handleAdopt(setting.id)}
                                                disabled={saving}
                                                className={`text-sm px-4 py-2 rounded-lg font-medium transition-colors ${isSuggestion
                                                    ? "bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300"
                                                    : "bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:bg-gray-50"
                                                    }`}
                                            >
                                                Adopt
                                            </button>
                                        </div>

                                        {/* Full list of meals */}
                                        <div className="grid grid-cols-1 gap-2 text-xs mt-3">
                                            {setting.timed_meals?.map((tm, i) => (
                                                <div key={i} className={`rounded p-2 border ${isSuggestion ? 'bg-blue-100/50 border-blue-200/50' : 'bg-gray-50 border-gray-200'}`}>
                                                    <p className={`font-semibold border-b pb-1 mb-1 flex items-baseline gap-1 ${isSuggestion ? 'border-blue-200/50 text-blue-900' : 'border-gray-200 text-gray-800'}`}>
                                                        {tm.name} <span className="text-[10px] font-normal capitalize opacity-70">({tm.meal_time?.replace("_", " ")})</span>
                                                    </p>
                                                    <div className={`flex justify-between text-[11px] ${isSuggestion ? 'text-blue-800' : 'text-gray-600'}`}>
                                                        <span>Calories: <span className="font-medium">{tm.calories_pct}%</span></span>
                                                        <span>Protein: <span className="font-medium">{tm.protein_g_pct}%</span></span>
                                                        <span>Carbs: <span className="font-medium">{tm.carbs_g_pct}%</span></span>
                                                        <span>Fat: <span className="font-medium">{tm.fat_g_pct}%</span></span>
                                                    </div>
                                                    {tm.meal_labels && tm.meal_labels.length > 0 && (
                                                        <div className="mt-1.5 flex flex-wrap gap-1">
                                                            {tm.meal_labels.map(lbl => (
                                                                <span key={lbl} className="inline-block px-1.5 py-0.5 bg-blue-200/60 text-blue-800 text-[9px] rounded-full font-medium capitalize">{lbl.replace(/_/g, " ")}</span>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Create Custom Setting */}
                <div>
                    <h2 className="text-xl font-semibold mb-4 text-gray-800">Create New Custom Plan</h2>
                    <form onSubmit={handleCreate} className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Plan Name</label>
                                <input
                                    type="text"
                                    value={newName}
                                    onChange={e => setNewName(e.target.value)}
                                    className="w-full border-gray-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                    required
                                />
                            </div>

                            <div className="flex justify-between items-center pt-2">
                                <h3 className="font-semibold text-gray-800">Meals ({timedMeals.length})</h3>
                                <button
                                    type="button"
                                    onClick={() => {
                                        if (timedMeals.length < 8) {
                                            setTimedMeals([...timedMeals, { name: `Meal ${timedMeals.length + 1}`, meal_time: "snack", calories_pct: 0, protein_g_pct: 0, carbs_g_pct: 0, fat_g_pct: 0, meal_labels: ["snack"] }]);
                                        }
                                    }}
                                    className="text-sm bg-blue-50 text-blue-700 hover:bg-blue-100 px-3 py-1.5 rounded-md font-medium"
                                >
                                    + Add Meal
                                </button>
                            </div>

                            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                                {timedMeals.map((tm, index) => (
                                    <div key={index} className="p-4 border border-gray-200 rounded-xl bg-gray-50 relative">
                                        {timedMeals.length > 1 && (
                                            <button
                                                type="button"
                                                onClick={() => setTimedMeals(timedMeals.filter((_, i) => i !== index))}
                                                className="absolute top-2 right-2 text-gray-400 hover:text-red-500 text-sm font-bold w-6 h-6 flex items-center justify-center rounded-full bg-white border border-gray-200 shadow-sm"
                                            >
                                                ✕
                                            </button>
                                        )}
                                        <div className="grid grid-cols-2 gap-3 mb-3 pr-6">
                                            <div>
                                                <label className="block text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Meal Name</label>
                                                <input
                                                    type="text"
                                                    value={tm.name}
                                                    onChange={e => {
                                                        const newArr = [...timedMeals];
                                                        newArr[index].name = e.target.value;
                                                        setTimedMeals(newArr);
                                                    }}
                                                    className="w-full border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500 sm:text-sm px-2 py-1 border"
                                                    required
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Time Type</label>
                                                <select
                                                    value={tm.meal_time}
                                                    onChange={e => {
                                                        const newArr = [...timedMeals];
                                                        const newTime = e.target.value;
                                                        newArr[index].meal_time = newTime;
                                                        // Auto-add the base meal_time label if not already present
                                                        if (!newArr[index].meal_labels.includes(newTime) && ALL_MEAL_LABELS.includes(newTime)) {
                                                            newArr[index].meal_labels = Array.from(new Set([newTime, ...newArr[index].meal_labels.filter(l => l !== newArr[index].meal_time)]));
                                                        }
                                                        setTimedMeals(newArr);
                                                    }}
                                                    className="w-full border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500 sm:text-sm px-2 py-1 border"
                                                >
                                                    <option value="breakfast">Breakfast</option>
                                                    <option value="lunch">Lunch</option>
                                                    <option value="dinner">Dinner</option>
                                                    <option value="snack">Snack</option>
                                                    <option value="pre_workout">Pre Workout</option>
                                                    <option value="post_workout">Post Workout</option>
                                                </select>
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-4 gap-2">
                                            <div>
                                                <label className="block text-[10px] text-gray-500 text-center">% KCal</label>
                                                <input type="number" min="0" max="100" value={tm.calories_pct}
                                                    onChange={e => { const a = [...timedMeals]; a[index].calories_pct = parseInt(e.target.value) || 0; setTimedMeals(a); }}
                                                    className="w-full text-center border-gray-300 rounded sm:text-sm px-1 py-1 border focus:ring-blue-500" required />
                                            </div>
                                            <div>
                                                <label className="block text-[10px] text-gray-500 text-center">% Prot</label>
                                                <input type="number" min="0" max="100" value={tm.protein_g_pct}
                                                    onChange={e => { const a = [...timedMeals]; a[index].protein_g_pct = parseInt(e.target.value) || 0; setTimedMeals(a); }}
                                                    className="w-full text-center border-gray-300 rounded sm:text-sm px-1 py-1 border focus:ring-blue-500" required />
                                            </div>
                                            <div>
                                                <label className="block text-[10px] text-gray-500 text-center">% Carb</label>
                                                <input type="number" min="0" max="100" value={tm.carbs_g_pct}
                                                    onChange={e => { const a = [...timedMeals]; a[index].carbs_g_pct = parseInt(e.target.value) || 0; setTimedMeals(a); }}
                                                    className="w-full text-center border-gray-300 rounded sm:text-sm px-1 py-1 border focus:ring-blue-500" required />
                                            </div>
                                            <div>
                                                <label className="block text-[10px] text-gray-500 text-center">% Fat</label>
                                                <input type="number" min="0" max="100" value={tm.fat_g_pct}
                                                    onChange={e => { const a = [...timedMeals]; a[index].fat_g_pct = parseInt(e.target.value) || 0; setTimedMeals(a); }}
                                                    className="w-full text-center border-gray-300 rounded sm:text-sm px-1 py-1 border focus:ring-blue-500" required />
                                            </div>
                                        </div>

                                        {/* Meal Label Chips */}
                                        <div className="mt-3">
                                            <label className="block text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1.5">Meal Labels (click to toggle)</label>
                                            <div className="flex flex-wrap gap-1.5">
                                                {ALL_MEAL_LABELS.map(lbl => {
                                                    const active = tm.meal_labels.includes(lbl);
                                                    return (
                                                        <button
                                                            key={lbl}
                                                            type="button"
                                                            onClick={() => {
                                                                const newArr = [...timedMeals];
                                                                if (active) {
                                                                    newArr[index].meal_labels = newArr[index].meal_labels.filter(l => l !== lbl);
                                                                } else {
                                                                    newArr[index].meal_labels = [...newArr[index].meal_labels, lbl];
                                                                }
                                                                setTimedMeals(newArr);
                                                            }}
                                                            className={`px-2 py-0.5 rounded-full text-[10px] font-medium capitalize border transition-all ${active
                                                                ? 'bg-blue-600 text-white border-blue-600'
                                                                : 'bg-white text-gray-500 border-gray-300 hover:border-blue-400 hover:text-blue-600'
                                                                }`}
                                                        >
                                                            {lbl.replace(/_/g, " ")}
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="flex justify-between items-center text-xs font-medium px-2 pt-2 border-t text-gray-500">
                                <span>Total Percentages:</span>
                                <span>
                                    <span className={timedMeals.reduce((a, b) => a + b.calories_pct, 0) !== 100 ? "text-red-500 mx-1" : "text-green-600 mx-1"}>{timedMeals.reduce((a, b) => a + b.calories_pct, 0)}% Kc</span>
                                    <span className={timedMeals.reduce((a, b) => a + b.protein_g_pct, 0) !== 100 ? "text-red-500 mx-1" : "text-green-600 mx-1"}>{timedMeals.reduce((a, b) => a + b.protein_g_pct, 0)}% P</span>
                                    <span className={timedMeals.reduce((a, b) => a + b.carbs_g_pct, 0) !== 100 ? "text-red-500 mx-1" : "text-green-600 mx-1"}>{timedMeals.reduce((a, b) => a + b.carbs_g_pct, 0)}% C</span>
                                    <span className={timedMeals.reduce((a, b) => a + b.fat_g_pct, 0) !== 100 ? "text-red-500 mx-1" : "text-green-600 mx-1"}>{timedMeals.reduce((a, b) => a + b.fat_g_pct, 0)}% F</span>
                                </span>
                            </div>

                            <button
                                type="submit"
                                disabled={saving}
                                className="w-full bg-gray-900 text-white font-medium py-2.5 rounded-xl hover:bg-gray-800 focus:ring-4 focus:ring-gray-200 transition-all active:scale-[0.98] disabled:opacity-50 mt-4"
                            >
                                {saving ? "Creating..." : "Create & Activate"}
                            </button>
                        </div>
                    </form>
                </div>

            </div>
        </div>
    );
}
