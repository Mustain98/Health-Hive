"use client";

import { useEffect, useState, FormEvent } from "react";
import { apiFetch } from "@/lib/api";
import type { GoalRead, GoalUpsert, GoalType, MilestoneType, GoalLogRead } from "@/lib/types";
import { GoalTrackerChart } from "@/components/ui/GoalTrackerChart";

// Milestone type → GoalType (matches the backend macro mapping).
const GOAL_FOR: Record<MilestoneType, GoalType> = {
    lose_weight: "lose", gain_weight: "gain", gain_muscle: "gain", maintain: "maintain",
};
const MILESTONE_LABELS: Record<MilestoneType, string> = {
    lose_weight: "Lose Weight", gain_weight: "Gain Weight", gain_muscle: "Gain Muscle", maintain: "Maintain Weight",
};

export default function GoalPage() {
    const [goal, setGoal] = useState<GoalRead | null>(null);
    const [form, setForm] = useState<GoalUpsert>({
        goal_type: "lose",
        milestone_type: "lose_weight",
        name: "",
        target_weight: null,
        target_value: null,
        unit: null,
        duration_days: null,
        start_date: null,
        end_date: null,
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [editing, setEditing] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    // Tracking state
    const [logs, setLogs] = useState<GoalLogRead[]>([]);
    const [weightInput, setWeightInput] = useState<string>("");
    const [loggingWeight, setLoggingWeight] = useState(false);

    useEffect(() => {
        async function loadGoal() {
            try {
                const data = await apiFetch<GoalRead>("/api/goal/me");
                setGoal(data);
                setForm({
                    goal_type: data.goal_type,
                    milestone_type: data.milestone_type ?? (data.goal_type === "lose" ? "lose_weight" : data.goal_type === "gain" ? "gain_weight" : "maintain"),
                    name: data.name ?? "",
                    target_weight: data.target_weight,
                    target_value: data.target_value,
                    unit: data.unit,
                    duration_days: data.duration_days,
                    start_date: data.start_date,
                    end_date: data.end_date,
                });
                // If goal exists, load tracking logs
                try {
                    const logsData = await apiFetch<GoalLogRead[]>(
                        `/api/goal/${data.id}/logs`,
                    );
                    setLogs(logsData);
                } catch (e) {
                    console.error("Failed to load goal tracking logs:", e);
                }
            } catch (error: any) {
                // 404 is expected if no goal set
                if (error.status !== 404) {
                    console.error("Failed to load goal:", error);
                }
            } finally {
                setLoading(false);
            }
        }
        loadGoal();
    }, []);

    async function handleLogWeight(e: FormEvent) {
        e.preventDefault();
        if (!weightInput || isNaN(Number(weightInput))) return;

        setLoggingWeight(true);
        try {
            const newLog = await apiFetch<GoalLogRead>("/api/goal/log", {
                method: "POST",
                body: { weight: Number(weightInput) },
            });
            setLogs((prev) => [...prev, newLog]);
            setWeightInput("");
        } catch (error: any) {
            alert(error.message);
        } finally {
            setLoggingWeight(false);
        }
    }

    async function handleSave(e: FormEvent) {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        const mt = form.milestone_type as MilestoneType;
        // Validation
        if ((mt === "lose_weight" || mt === "gain_weight") && (!form.target_weight || form.target_weight <= 0)) {
            setMessage("Error: Target weight must be greater than 0 for weight milestones");
            setSaving(false);
            return;
        }
        if (mt === "gain_muscle" && (!form.target_value || form.target_value <= 0)) {
            setMessage("Error: Enter how many kg of muscle you want to gain");
            setSaving(false);
            return;
        }

        const payload: GoalUpsert = { ...form, goal_type: GOAL_FOR[mt] };
        if (mt === "maintain") { payload.target_weight = null; payload.target_value = null; }
        if (mt === "gain_muscle") { payload.target_weight = null; payload.unit = "kg_muscle"; }
        else { payload.target_value = null; }

        try {
            const data = await apiFetch<GoalRead>("/api/goal/me", {
                method: "PUT",
                body: payload,
            });
            setGoal(data);
            setEditing(false);
            setMessage("Goal saved successfully!");
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setSaving(false);
        }
    }

    async function handleUpdateDate() {
        if (!goal) return;
        setSaving(true);
        setMessage(null);
        try {
            await apiFetch(`/api/goal/${goal.id}/change-date`, {
                method: "PATCH",
                body: { new_start_date: form.start_date || "" },
            });
            const updatedData = await apiFetch<GoalRead>("/api/goal/me");
            setGoal(updatedData);
            setMessage("Goal date updated successfully!");
        } catch (error: any) {
            setMessage(`Error updating date: ${error.message}`);
        } finally {
            setSaving(false);
        }
    }

    async function handleDelete() {
        if (!confirm("Are you sure you want to delete your goal?")) return;

        setSaving(true);
        setMessage(null);

        try {
            await apiFetch("/api/goal/me", { method: "DELETE" });
            setGoal(null);
            setForm({
                goal_type: "lose",
                milestone_type: "lose_weight",
                name: "",
                target_weight: null,
                target_value: null,
                unit: null,
                duration_days: null,
                start_date: null,
                end_date: null,
            });
            setMessage("Goal deleted successfully");
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setSaving(false);
        }
    }

    if (loading) {
        return <div className="text-center py-12">Loading...</div>;
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">My Goal</h1>
                <p className="mt-2 text-sm text-gray-600">
                    Set and track your weight goals manually
                </p>
            </div>

            {message && (
                <div
                    className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}
                >
                    <p
                        className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}
                    >
                        {message}
                    </p>
                </div>
            )}

            <form
                onSubmit={handleSave}
                className="bg-white shadow rounded-lg p-6 space-y-6"
            >
                <div>
                    <label className="block text-sm font-medium text-gray-700">
                        Milestone Type
                    </label>
                    <select
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border disabled:bg-gray-100 disabled:text-gray-500"
                        value={form.milestone_type ?? "lose_weight"}
                        disabled={!!goal && !editing}
                        onChange={(e) => {
                            const mt = e.target.value as MilestoneType;
                            setForm({ ...form, milestone_type: mt, goal_type: GOAL_FOR[mt] });
                        }}
                    >
                        {(Object.keys(MILESTONE_LABELS) as MilestoneType[]).map((mt) => (
                            <option key={mt} value={mt}>{MILESTONE_LABELS[mt]}</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700">
                        Milestone Name (optional)
                    </label>
                    <input
                        type="text"
                        disabled={!!goal && !editing}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border disabled:bg-gray-100 disabled:text-gray-500"
                        value={form.name ?? ""}
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                        placeholder="e.g., Lose 10kg for summer"
                    />
                </div>

                {(form.milestone_type === "lose_weight" || form.milestone_type === "gain_weight") && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Target Weight (kg)
                        </label>
                        <input
                            type="number"
                            step="0.1"
                            min="0.1"
                            disabled={!!goal && !editing}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border disabled:bg-gray-100 disabled:text-gray-500"
                            value={form.target_weight ?? ""}
                            onChange={(e) =>
                                setForm({ ...form, target_weight: e.target.value ? Number(e.target.value) : null })
                            }
                            placeholder={form.milestone_type === "lose_weight" ? "e.g., 70" : "e.g., 80"}
                        />
                        <p className="mt-1 text-sm text-gray-500">Your target weight to reach</p>
                    </div>
                )}

                {form.milestone_type === "gain_muscle" && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Muscle to gain (kg)
                        </label>
                        <input
                            type="number"
                            step="0.1"
                            min="0.1"
                            disabled={!!goal && !editing}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border disabled:bg-gray-100 disabled:text-gray-500"
                            value={form.target_value ?? ""}
                            onChange={(e) =>
                                setForm({ ...form, target_value: e.target.value ? Number(e.target.value) : null })
                            }
                            placeholder="e.g., 2"
                        />
                        <p className="mt-1 text-sm text-gray-500">Total muscle mass to gain over the duration</p>
                    </div>
                )}

                {goal && goal.initial_weight != null && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Initial Weight (kg)
                        </label>
                        <input
                            type="number"
                            disabled
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border bg-gray-100 text-gray-500 cursor-not-allowed"
                            value={goal.initial_weight}
                        />
                        <p className="mt-1 text-sm text-gray-500">
                            Automatically logged when goal was activated.
                        </p>
                    </div>
                )}

                <div>
                    <label className="block text-sm font-medium text-gray-700">
                        Duration (days) - Optional
                    </label>
                    <input
                        type="number"
                        min="1"
                        disabled={!!goal && !editing}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border disabled:bg-gray-100 disabled:text-gray-500"
                        value={form.duration_days ?? ""}
                        onChange={(e) =>
                            setForm({
                                ...form,
                                duration_days: e.target.value ? Number(e.target.value) : null,
                            })
                        }
                        placeholder="e.g., 30"
                    />
                </div>

                <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Start Date - Optional
                        </label>
                        <input
                            type="date"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.start_date || ""}
                            onChange={(e) =>
                                setForm({ ...form, start_date: e.target.value || null })
                            }
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            End Date (Auto-calculated)
                        </label>
                        <input
                            type="date"
                            disabled
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border disabled:bg-gray-100 disabled:text-gray-500"
                            value={form.end_date || ""}
                            onChange={(e) =>
                                setForm({ ...form, end_date: e.target.value || null })
                            }
                        />
                    </div>
                </div>

                <div className="flex justify-between flex-wrap gap-4">
                    {goal && (
                        <button
                            type="button"
                            onClick={handleDelete}
                            disabled={saving}
                            className="inline-flex justify-center py-2 px-4 border border-red-300 shadow-sm text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                        >
                            Deactive Goal
                        </button>
                    )}
                    <div className="flex gap-2 ml-auto">
                        {goal && !editing && (
                            <button
                                type="button"
                                onClick={() => setEditing(true)}
                                className="inline-flex justify-center py-2 px-4 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                            >
                                Edit
                            </button>
                        )}
                        {goal && !editing && (
                            <button
                                type="button"
                                onClick={handleUpdateDate}
                                disabled={saving}
                                className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                            >
                                {saving ? "Updating Date..." : "Update Date"}
                            </button>
                        )}
                        {(!goal || editing) && (
                            <button
                                type="submit"
                                disabled={saving}
                                className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                            >
                                {saving ? "Saving..." : editing ? "Save changes" : "Create Goal"}
                            </button>
                        )}
                        {editing && (
                            <button
                                type="button"
                                onClick={() => setEditing(false)}
                                className="inline-flex justify-center py-2 px-4 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-600 bg-white hover:bg-gray-50"
                            >
                                Cancel
                            </button>
                        )}
                    </div>
                </div>
            </form>

            {goal && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-blue-900 mb-2">
                        Current Goal
                    </h3>
                    <dl className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2">
                        <div>
                            <dt className="text-sm text-blue-700">Type:</dt>
                            <dd className="text-sm font-medium text-blue-900 capitalize">
                                {goal.goal_type}
                            </dd>
                        </div>
                        {goal.target_weight && (
                            <div>
                                <dt className="text-sm text-blue-700">Target Weight:</dt>
                                <dd className="text-sm font-medium text-blue-900">
                                    {goal.target_weight} kg
                                </dd>
                            </div>
                        )}
                        {goal.initial_weight && (
                            <div>
                                <dt className="text-sm text-blue-700">Initial Weight:</dt>
                                <dd className="text-sm font-medium text-blue-900">
                                    {goal.initial_weight} kg
                                </dd>
                            </div>
                        )}
                        {goal.duration_days && (
                            <div>
                                <dt className="text-sm text-blue-700">Duration:</dt>
                                <dd className="text-sm font-medium text-blue-900">
                                    {goal.duration_days} days
                                </dd>
                            </div>
                        )}
                    </dl>
                </div>
            )}

            {/* Goal Tracker Section (only shown if goal is actively set) */}
            {goal && (
                <div className="bg-white shadow rounded-lg p-6 space-y-6">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">Goal Progress</h2>
                            <p className="mt-1 text-sm text-gray-500">
                                Track your weight to see if you're hitting your target.
                            </p>
                        </div>

                        <form
                            onSubmit={handleLogWeight}
                            className="flex gap-2 items-center"
                        >
                            <input
                                type="number"
                                step="0.1"
                                required
                                value={weightInput}
                                onChange={(e) => setWeightInput(e.target.value)}
                                placeholder="Today's Weight (kg)"
                                className="block w-40 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            />
                            <button
                                type="submit"
                                disabled={loggingWeight || !weightInput}
                                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                            >
                                {loggingWeight ? "Logging..." : "Log"}
                            </button>
                        </form>
                    </div>

                    <div className="border border-gray-100 rounded-lg p-4 bg-gray-50">
                        <GoalTrackerChart
                            logs={logs}
                            goalType={goal.goal_type}
                            targetWeight={goal.target_weight ?? null}
                            initialWeight={goal.initial_weight ?? null}
                        />
                    </div>

                    {logs.length > 0 && (
                        <div className="mt-4">
                            <h3 className="text-sm font-medium text-gray-900 mb-3">
                                Recent Logs
                            </h3>
                            <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 rounded-lg">
                                <table className="min-w-full divide-y divide-gray-300">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th
                                                scope="col"
                                                className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900"
                                            >
                                                Date
                                            </th>
                                            <th
                                                scope="col"
                                                className="px-3 py-3.5 text-right text-sm font-semibold text-gray-900"
                                            >
                                                Weight
                                            </th>
                                            <th
                                                scope="col"
                                                className="px-3 py-3.5 text-right text-sm font-semibold text-gray-900"
                                            >
                                                Due Target (Delta)
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-200 bg-white">
                                        {[...logs]
                                            .reverse()
                                            .slice(0, 5)
                                            .map((log) => (
                                                <tr key={log.id}>
                                                    <td className="whitespace-nowrap py-3 pl-4 pr-3 text-sm text-gray-500">
                                                        {new Date(log.date).toLocaleDateString()}{" "}
                                                        {new Date(log.date).toLocaleTimeString([], {
                                                            hour: "2-digit",
                                                            minute: "2-digit",
                                                        })}
                                                    </td>
                                                    <td className="whitespace-nowrap px-3 py-3 text-sm text-gray-900 text-right font-medium">
                                                        {log.weight} kg
                                                    </td>
                                                    <td className="whitespace-nowrap px-3 py-3 text-sm text-gray-500 text-right">
                                                        {log.due_terget.toFixed(2)} kg
                                                    </td>
                                                </tr>
                                            ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
