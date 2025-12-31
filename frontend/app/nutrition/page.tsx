"use client";

import { useEffect, useState, FormEvent } from "react";
import { apiFetch } from "@/lib/api";
import type { NutritionTargetRead, NutritionTargetUpdate } from "@/lib/types";

export default function NutritionPage() {
    const [target, setTarget] = useState<NutritionTargetRead | null>(null);
    const [form, setForm] = useState<NutritionTargetUpdate>({
        calories_kcal: null,
        protein_g: null,
        carbs_g: null,
        fat_g: null,
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    useEffect(() => {
        async function loadTarget() {
            try {
                const data = await apiFetch<NutritionTargetRead>("/api/nutrition-target/me");
                setTarget(data);
                setForm({
                    calories_kcal: data.calories_kcal,
                    protein_g: data.protein_g,
                    carbs_g: data.carbs_g,
                    fat_g: data.fat_g,
                });
            } catch (error: any) {
                // 404 is expected if no target set
                if (error.status !== 404) {
                    console.error("Failed to load nutrition target:", error);
                }
            } finally {
                setLoading(false);
            }
        }
        loadTarget();
    }, []);

    async function handleSave(e: FormEvent) {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        try {
            const data = await apiFetch<NutritionTargetRead>("/api/nutrition-target/me", {
                method: "PUT",
                body: form,
            });
            setTarget(data);
            setMessage("Nutrition targets saved successfully!");
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setSaving(false);
        }
    }

    if (loading) {
        return <div className="text-center py-12">Loading...</div>;
    }

    // Calculate calories from macros for reference
    const calculatedCalories =
        (form.protein_g || 0) * 4 +
        (form.carbs_g || 0) * 4 +
        (form.fat_g || 0) * 9;

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Nutrition Targets</h1>
                <p className="mt-2 text-sm text-gray-600">
                    Set your daily macro and calorie targets manually
                </p>
            </div>

            {message && (
                <div className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                    <p className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                        {message}
                    </p>
                </div>
            )}

            <form onSubmit={handleSave} className="bg-white shadow rounded-lg p-6 space-y-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700">
                        Daily Calories (kcal)
                    </label>
                    <input
                        type="number"
                        min="800"
                        max="10000"
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                        value={form.calories_kcal ?? ""}
                        onChange={(e) => setForm({ ...form, calories_kcal: e.target.value ? Number(e.target.value) : null })}
                        placeholder="e.g., 2000"
                    />
                    <p className="mt-1 text-sm text-gray-500">Range: 800-10000 kcal</p>
                </div>

                <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Protein (g)
                        </label>
                        <input
                            type="number"
                            min="0"
                            max="400"
                            step="0.1"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.protein_g ?? ""}
                            onChange={(e) => setForm({ ...form, protein_g: e.target.value ? Number(e.target.value) : null })}
                            placeholder="e.g., 150"
                        />
                        <p className="mt-1 text-sm text-gray-500">Max: 400g</p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Carbs (g)
                        </label>
                        <input
                            type="number"
                            min="0"
                            max="1200"
                            step="0.1"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.carbs_g ?? ""}
                            onChange={(e) => setForm({ ...form, carbs_g: e.target.value ? Number(e.target.value) : null })}
                            placeholder="e.g., 200"
                        />
                        <p className="mt-1 text-sm text-gray-500">Max: 1200g</p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Fat (g)
                        </label>
                        <input
                            type="number"
                            min="0"
                            max="300"
                            step="0.1"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.fat_g ?? ""}
                            onChange={(e) => setForm({ ...form, fat_g: e.target.value ? Number(e.target.value) : null })}
                            placeholder="e.g., 65"
                        />
                        <p className="mt-1 text-sm text-gray-500">Max: 300g</p>
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

                <div className="flex justify-end">
                    <button
                        type="submit"
                        disabled={saving}
                        className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                    >
                        {saving ? "Saving..." : target ? "Update Targets" : "Create Targets"}
                    </button>
                </div>
            </form>

            {target && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-green-900 mb-2">Current Targets</h3>
                    <dl className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-4">
                        <div>
                            <dt className="text-sm text-green-700">Calories:</dt>
                            <dd className="text-sm font-medium text-green-900">{target.calories_kcal} kcal</dd>
                        </div>
                        <div>
                            <dt className="text-sm text-green-700">Protein:</dt>
                            <dd className="text-sm font-medium text-green-900">{target.protein_g}g</dd>
                        </div>
                        <div>
                            <dt className="text-sm text-green-700">Carbs:</dt>
                            <dd className="text-sm font-medium text-green-900">{target.carbs_g}g</dd>
                        </div>
                        <div>
                            <dt className="text-sm text-green-700">Fat:</dt>
                            <dd className="text-sm font-medium text-green-900">{target.fat_g}g</dd>
                        </div>
                    </dl>
                </div>
            )}
        </div>
    );
}
