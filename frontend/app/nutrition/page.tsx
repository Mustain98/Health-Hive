"use client";

import { useEffect, useState, FormEvent } from "react";
import { apiFetch } from "@/lib/api";
import type { NutritionTargetRead, NutritionTargetUpdate } from "@/lib/types";
import { CheckCircle, Plus } from "lucide-react";
import { useAuth } from "@/components/guards/AuthGuard";

export default function NutritionPage() {
    const { user } = useAuth();
    const [targets, setTargets] = useState<NutritionTargetRead[]>([]);
    const [isFormOpen, setIsFormOpen] = useState(false);

    const [form, setForm] = useState<NutritionTargetUpdate>({
        calories_kcal: null,
        protein_g: null,
        carbs_g: null,
        fat_g: null,
    });

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [activatingId, setActivatingId] = useState<string | null>(null);
    const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

    useEffect(() => {
        loadTargets();
    }, []);

    async function loadTargets() {
        setLoading(true);
        try {
            const data = await apiFetch<NutritionTargetRead[]>("/api/nutrition-target/all");
            setTargets(data || []);
        } catch (error: any) {
            console.error("Failed to load targets:", error);
        } finally {
            setLoading(false);
        }
    }

    async function handleSave(e: FormEvent) {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        try {
            await apiFetch<NutritionTargetRead>("/api/nutrition-target/me", {
                method: "PUT",
                body: form,
            });
            setMessage({ text: "Nutrition targets created and activated successfully!", type: "success" });
            setIsFormOpen(false);
            setForm({
                calories_kcal: null,
                protein_g: null,
                carbs_g: null,
                fat_g: null,
            });
            await loadTargets();
        } catch (error: any) {
            setMessage({ text: `Error: ${error.message}`, type: "error" });
        } finally {
            setSaving(false);
        }
    }

    async function handleActivate(targetId: string | number) {
        setActivatingId(String(targetId));
        setMessage(null);
        try {
            await apiFetch<NutritionTargetRead>(`/api/nutrition-target/${targetId}/activate`, {
                method: "PUT",
            });
            setMessage({ text: "Nutrition target activated successfully!", type: "success" });
            await loadTargets();
        } catch (error: any) {
            setMessage({ text: `Failed to activate: ${error.message}`, type: "error" });
        } finally {
            setActivatingId(null);
        }
    }

    if (loading) {
        return (
            <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    const calculatedCalories =
        (form.protein_g || 0) * 4 +
        (form.carbs_g || 0) * 4 +
        (form.fat_g || 0) * 9;

    const currentTarget = targets.find(t => t.active);
    const otherTargets = targets.filter(t => !t.active);

    return (
        <div className="space-y-6">
            <div className="sm:flex sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Nutrition Targets</h1>
                    <p className="mt-2 text-sm text-gray-600">
                        Manage your daily macro and calorie targets
                    </p>
                </div>
                <div className="mt-4 sm:ml-16 sm:mt-0 sm:flex-none">
                    <button
                        type="button"
                        onClick={() => setIsFormOpen(!isFormOpen)}
                        className="inline-flex items-center gap-x-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                    >
                        {isFormOpen ? (
                            "Cancel"
                        ) : (
                            <>
                                <Plus aria-hidden="true" className="-ml-0.5 size-5" />
                                Create New Target
                            </>
                        )}
                    </button>
                </div>
            </div>

            {message && (
                <div className={`rounded-md p-4 ${message.type === "error" ? "bg-red-50 text-red-800" : "bg-green-50 text-green-800"}`}>
                    <p className="text-sm">{message.text}</p>
                </div>
            )}

            {isFormOpen && (
                <form onSubmit={handleSave} className="bg-white shadow rounded-lg p-6 space-y-6 ring-1 ring-gray-900/5">
                    <div>
                        <h2 className="text-base/7 font-semibold text-gray-900">New Nutrition Target</h2>
                        <p className="mt-1 text-sm/6 text-gray-600">Set custom targets for your daily intake.</p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Daily Calories (kcal)
                        </label>
                        <input
                            required
                            type="number"
                            min="800"
                            max="10000"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
                            value={form.calories_kcal ?? ""}
                            onChange={(e) => setForm({ ...form, calories_kcal: e.target.value ? Number(e.target.value) : null })}
                            placeholder="e.g., 2000"
                        />
                    </div>

                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">
                                Protein (g)
                            </label>
                            <input
                                required
                                type="number"
                                min="0"
                                max="400"
                                step="0.1"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
                                value={form.protein_g ?? ""}
                                onChange={(e) => setForm({ ...form, protein_g: e.target.value ? Number(e.target.value) : null })}
                                placeholder="e.g., 150"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700">
                                Carbs (g)
                            </label>
                            <input
                                required
                                type="number"
                                min="0"
                                max="1200"
                                step="0.1"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
                                value={form.carbs_g ?? ""}
                                onChange={(e) => setForm({ ...form, carbs_g: e.target.value ? Number(e.target.value) : null })}
                                placeholder="e.g., 200"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700">
                                Fat (g)
                            </label>
                            <input
                                required
                                type="number"
                                min="0"
                                max="300"
                                step="0.1"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
                                value={form.fat_g ?? ""}
                                onChange={(e) => setForm({ ...form, fat_g: e.target.value ? Number(e.target.value) : null })}
                                placeholder="e.g., 65"
                            />
                        </div>
                    </div>

                    {calculatedCalories > 0 && (
                        <div className="bg-gray-50 border border-gray-200 rounded p-4">
                            <p className="text-sm text-gray-700">
                                <span className="font-medium">Calculated from macros:</span>{" "}
                                ~{Math.round(calculatedCalories)} kcal
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                                Protein: {(form.protein_g || 0) * 4} + Carbs: {(form.carbs_g || 0) * 4} + Fat: {(form.fat_g || 0) * 9}
                            </p>
                        </div>
                    )}

                    <div className="flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={() => setIsFormOpen(false)}
                            className="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={saving}
                            className="inline-flex justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50"
                        >
                            {saving ? "Saving..." : "Save & Activate"}
                        </button>
                    </div>
                </form>
            )}

            {/* Current Active Target Section */}
            <div className="bg-white shadow sm:rounded-lg ring-1 ring-gray-900/5">
                <div className="px-4 py-5 sm:px-6 flex items-center justify-between">
                    <div>
                        <h3 className="text-base leading-6 font-semibold text-gray-900">Current Active Target</h3>
                        <p className="mt-1 max-w-2xl text-sm text-gray-500">
                            The target you are currently tracking against.
                        </p>
                    </div>
                    {currentTarget && (
                        <span className="inline-flex items-center gap-x-1.5 rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-700">
                            <CheckCircle className="h-4 w-4" aria-hidden="true" />
                            Active
                        </span>
                    )}
                </div>

                {currentTarget ? (
                    <div className="border-t border-gray-200 px-4 py-5 sm:px-6">
                        <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-4 lg:grid-cols-5">
                            <div className="sm:col-span-1">
                                <dt className="text-sm font-medium text-gray-500">Calories</dt>
                                <dd className="mt-1 text-sm text-gray-900">{currentTarget.calories_kcal} kcal</dd>
                            </div>
                            <div className="sm:col-span-1">
                                <dt className="text-sm font-medium text-gray-500">Protein</dt>
                                <dd className="mt-1 text-sm text-gray-900">{currentTarget.protein_g}g</dd>
                            </div>
                            <div className="sm:col-span-1">
                                <dt className="text-sm font-medium text-gray-500">Carbs</dt>
                                <dd className="mt-1 text-sm text-gray-900">{currentTarget.carbs_g}g</dd>
                            </div>
                            <div className="sm:col-span-1">
                                <dt className="text-sm font-medium text-gray-500">Fat</dt>
                                <dd className="mt-1 text-sm text-gray-900">{currentTarget.fat_g}g</dd>
                            </div>
                            <div className="sm:col-span-1">
                                <dt className="text-sm font-medium text-gray-500">Created</dt>
                                <dd className="mt-1 text-sm text-gray-900">
                                    {new Date(currentTarget.created_at).toLocaleDateString()}
                                    {currentTarget.created_by !== user?.id && currentTarget.created_by_name && (
                                        <div className="text-xs text-indigo-600 mt-1">Suggested by {currentTarget.created_by_name}</div>
                                    )}
                                </dd>
                            </div>
                        </dl>
                    </div>
                ) : (
                    <div className="border-t border-gray-200 px-4 py-5 sm:px-6 text-sm text-gray-500">
                        No active nutrition target found. Create one above or activate a previous/suggested target below.
                    </div>
                )}
            </div>

            {/* Other Targets List */}
            {otherTargets.length > 0 && (
                <div className="bg-white shadow sm:rounded-lg ring-1 ring-gray-900/5">
                    <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
                        <h3 className="text-base leading-6 font-semibold text-gray-900">Past & Suggested Targets</h3>
                        <p className="mt-1 max-w-2xl text-sm text-gray-500">
                            Previously active targets and consultant suggestions.
                        </p>
                    </div>
                    <ul role="list" className="divide-y divide-gray-100">
                        {otherTargets.map((t) => (
                            <li key={t.id} className="flex flex-wrap items-center justify-between gap-x-6 gap-y-4 px-4 py-5 sm:px-6 hover:bg-gray-50">
                                <dl className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-4 lg:grid-cols-5 w-full sm:w-auto flex-1">
                                    <div className="sm:col-span-1">
                                        <dt className="text-xs font-medium text-gray-500 uppercase tracking-wide">Calories</dt>
                                        <dd className="mt-1 text-sm text-gray-900">{t.calories_kcal} kcal</dd>
                                    </div>
                                    <div className="sm:col-span-1">
                                        <dt className="text-xs font-medium text-gray-500 uppercase tracking-wide">Macros</dt>
                                        <dd className="mt-1 text-sm text-gray-900 text-nowrap">
                                            {t.protein_g}P / {t.carbs_g}C / {t.fat_g}F
                                        </dd>
                                    </div>
                                    <div className="sm:col-span-2">
                                        <dt className="text-xs font-medium text-gray-500 uppercase tracking-wide">Details</dt>
                                        <dd className="mt-1 text-sm text-gray-900">
                                            <div>Created: {new Date(t.created_at).toLocaleDateString()}</div>
                                            {t.created_by !== user?.id && t.created_by_name && (
                                                <div className="text-xs text-indigo-600 font-medium">Suggested by {t.created_by_name}</div>
                                            )}
                                        </dd>
                                    </div>
                                </dl>
                                <div className="flex shrink-0 items-center gap-x-4">
                                    <button
                                        type="button"
                                        onClick={() => handleActivate(t.id)}
                                        disabled={activatingId === String(t.id)}
                                        className="rounded-md bg-white px-2.5 py-1.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50"
                                    >
                                        {activatingId === String(t.id) ? "Activating..." : "Activate"}
                                    </button>
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
