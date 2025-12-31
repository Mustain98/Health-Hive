"use client";

import { useEffect, useState, FormEvent } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { GoalRead, GoalUpsert, NutritionTargetRead, NutritionTargetUpdate, GoalType } from "@/lib/types";

export default function ClientManagementPage() {
    const params = useParams();
    const userId = Number(params.userId);

    const [activeTab, setActiveTab] = useState<"goal" | "nutrition">("goal");
    const [hasPermission, setHasPermission] = useState(true);
    const [goal, setGoal] = useState<GoalRead | null>(null);
    const [nutrition, setNutrition] = useState<NutritionTargetRead | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    // Forms
    const [goalForm, setGoalForm] = useState<GoalUpsert>({
        goal_type: "lose",
        target_delta_kg: null,
        duration_days: null,
    });

    const [nutritionForm, setNutritionForm] = useState<NutritionTargetUpdate>({
        calories_kcal: null,
        protein_g: null,
        carbs_g: null,
        fat_g: null,
    });

    useEffect(() => {
        loadClientData();
    }, [userId, activeTab]);

    async function loadClientData() {
        setLoading(true);
        setMessage(null);

        try {
            if (activeTab === "goal") {
                const data = await apiFetch<GoalRead>(`/api/consultant/users/${userId}/goal`);
                setGoal(data);
                setGoalForm({
                    goal_type: data.goal_type,
                    target_delta_kg: data.target_delta_kg,
                    duration_days: data.duration_days,
                    start_date: data.start_date,
                    end_date: data.end_date,
                });
            } else {
                const data = await apiFetch<NutritionTargetRead>(`/api/consultant/users/${userId}/nutrition-target`);
                setNutrition(data);
                setNutritionForm({
                    calories_kcal: data.calories_kcal,
                    protein_g: data.protein_g,
                    carbs_g: data.carbs_g,
                    fat_g: data.fat_g,
                });
            }
            setHasPermission(true);
        } catch (error: any) {
            if (error.status === 403) {
                setHasPermission(false);
                setMessage("Permission denied. The client must grant you access to edit their data.");
            } else if (error.status === 404) {
                setMessage(`No ${activeTab} data found for this client.`);
            } else {
                console.error("Failed to load client data:", error);
                setMessage(`Error: ${error.message}`);
            }
        } finally {
            setLoading(false);
        }
    }

    async function handleSaveGoal(e: FormEvent) {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        try {
            const data = await apiFetch<GoalRead>(`/api/consultant/users/${userId}/goal`, {
                method: "PUT",
                body: goalForm,
            });
            setGoal(data);
            setMessage("Client goal updated successfully!");
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setSaving(false);
        }
    }

    async function handleSaveNutrition(e: FormEvent) {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        try {
            const data = await apiFetch<NutritionTargetRead>(`/api/consultant/users/${userId}/nutrition-target`, {
                method: "PUT",
                body: nutritionForm,
            });
            setNutrition(data);
            setMessage("Client nutrition targets updated successfully!");
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="space-y-6">
            <div>
                <Link href="/consultant/appointments" className="text-sm text-blue-600 hover:text-blue-500">
                    ← Back to appointments
                </Link>
                <h1 className="text-3xl font-bold text-gray-900 mt-2">Client #{userId}</h1>
                <p className="mt-2 text-sm text-gray-600">
                    Update client's goals and nutrition targets
                </p>
            </div>

            {message && (
                <div className={`rounded-md p-4 ${message.includes("Error") || message.includes("denied") ? "bg-red-50" : "bg-green-50"}`}>
                    <p className={`text-sm ${message.includes("Error") || message.includes("denied") ? "text-red-800" : "text-green-800"}`}>
                        {message}
                    </p>
                </div>
            )}

            {!hasPermission ? (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
                    <h3 className="text-lg font-medium text-yellow-900 mb-2">Permission Required</h3>
                    <p className="text-sm text-yellow-700">
                        You don't have permission to edit this client's data. The client needs to grant you access from their Permissions page.
                    </p>
                </div>
            ) : (
                <>
                    {/* Tabs */}
                    <div className="border-b border-gray-200">
                        <nav className="-mb-px flex space-x-8">
                            <button
                                onClick={() => setActiveTab("goal")}
                                className={`${activeTab === "goal"
                                        ? "border-blue-500 text-blue-600"
                                        : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                                    } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                            >
                                Goal
                            </button>
                            <button
                                onClick={() => setActiveTab("nutrition")}
                                className={`${activeTab === "nutrition"
                                        ? "border-blue-500 text-blue-600"
                                        : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                                    } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                            >
                                Nutrition Targets
                            </button>
                        </nav>
                    </div>

                    {/* Content */}
                    {loading ? (
                        <div className="text-center py-12">Loading...</div>
                    ) : activeTab === "goal" ? (
                        <form onSubmit={handleSaveGoal} className="bg-white shadow rounded-lg p-6 space-y-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Goal Type</label>
                                <select
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                    value={goalForm.goal_type}
                                    onChange={(e) => setGoalForm({ ...goalForm, goal_type: e.target.value as GoalType })}
                                >
                                    <option value="lose">Lose Weight</option>
                                    <option value="gain">Gain Weight</option>
                                    <option value="maintain">Maintain Weight</option>
                                </select>
                            </div>

                            {goalForm.goal_type !== "maintain" && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">
                                        Target Weight Change (kg)
                                    </label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                        value={goalForm.target_delta_kg ?? ""}
                                        onChange={(e) => setGoalForm({ ...goalForm, target_delta_kg: e.target.value ? Number(e.target.value) : null })}
                                    />
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Duration (days)</label>
                                <input
                                    type="number"
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                    value={goalForm.duration_days ?? ""}
                                    onChange={(e) => setGoalForm({ ...goalForm, duration_days: e.target.value ? Number(e.target.value) : null })}
                                />
                            </div>

                            <div className="flex justify-end">
                                <button
                                    type="submit"
                                    disabled={saving}
                                    className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                                >
                                    {saving ? "Saving..." : "Update Goal"}
                                </button>
                            </div>
                        </form>
                    ) : (
                        <form onSubmit={handleSaveNutrition} className="bg-white shadow rounded-lg p-6 space-y-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Daily Calories (kcal)</label>
                                <input
                                    type="number"
                                    min="800"
                                    max="10000"
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                    value={nutritionForm.calories_kcal ?? ""}
                                    onChange={(e) => setNutritionForm({ ...nutritionForm, calories_kcal: e.target.value ? Number(e.target.value) : null })}
                                />
                            </div>

                            <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Protein (g)</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                        value={nutritionForm.protein_g ?? ""}
                                        onChange={(e) => setNutritionForm({ ...nutritionForm, protein_g: e.target.value ? Number(e.target.value) : null })}
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Carbs (g)</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                        value={nutritionForm.carbs_g ?? ""}
                                        onChange={(e) => setNutritionForm({ ...nutritionForm, carbs_g: e.target.value ? Number(e.target.value) : null })}
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Fat (g)</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                        value={nutritionForm.fat_g ?? ""}
                                        onChange={(e) => setNutritionForm({ ...nutritionForm, fat_g: e.target.value ? Number(e.target.value) : null })}
                                    />
                                </div>
                            </div>

                            <div className="flex justify-end">
                                <button
                                    type="submit"
                                    disabled={saving}
                                    className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                                >
                                    {saving ? "Saving..." : "Update Nutrition Targets"}
                                </button>
                            </div>
                        </form>
                    )}
                </>
            )}
        </div>
    );
}
