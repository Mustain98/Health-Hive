"use client";

import { useEffect, useState, FormEvent } from "react";
import { apiFetch } from "@/lib/api";
import type { GoalRead, GoalUpsert, GoalType, GoalLogRead } from "@/lib/types";
import { GoalTrackerChart } from "@/components/ui/GoalTrackerChart";

export default function GoalPage() {
    const [goal, setGoal] = useState<GoalRead | null>(null);
    const [form, setForm] = useState<GoalUpsert>({
        goal_type: "lose",
        target_delta_kg: null,
        duration_days: null,
        start_date: null,
        end_date: null,
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
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
                    target_delta_kg: data.target_delta_kg,
                    duration_days: data.duration_days,
                    start_date: data.start_date,
                    end_date: data.end_date,
                });
                // If goal exists, load tracking logs
                try {
                    const logsData = await apiFetch<GoalLogRead[]>(`/api/goal/${data.id}/logs`);
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

        // Validation
        if (form.goal_type !== "maintain" && (!form.target_delta_kg || form.target_delta_kg <= 0)) {
            setMessage("Error: Target weight change must be greater than 0 for lose/gain goals");
            setSaving(false);
            return;
        }

        if (form.goal_type === "maintain") {
            form.target_delta_kg = null;
        }

        try {
            const data = await apiFetch<GoalRead>("/api/goal/me", {
                method: "PUT",
                body: form,
            });
            setGoal(data);
            setMessage("Goal saved successfully!");
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
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
                target_delta_kg: null,
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
                <div className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                    <p className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                        {message}
                    </p>
                </div>
            )}

            <form onSubmit={handleSave} className="bg-white shadow rounded-lg p-6 space-y-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700">Goal Type</label>
                    <select
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                        value={form.goal_type}
                        onChange={(e) => setForm({ ...form, goal_type: e.target.value as GoalType })}
                    >
                        <option value="lose">Lose Weight</option>
                        <option value="gain">Gain Weight</option>
                        <option value="maintain">Maintain Weight</option>
                    </select>
                </div>

                {form.goal_type !== "maintain" && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Target Weight Change (kg)
                        </label>
                        <input
                            type="number"
                            step="0.1"
                            min="0.1"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.target_delta_kg ?? ""}
                            onChange={(e) => setForm({ ...form, target_delta_kg: e.target.value ? Number(e.target.value) : null })}
                            placeholder={form.goal_type === "lose" ? "e.g., 5" : "e.g., 3"}
                        />
                        <p className="mt-1 text-sm text-gray-500">
                            {form.goal_type === "lose" ? "How much weight to lose" : "How much weight to gain"}
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
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                        value={form.duration_days ?? ""}
                        onChange={(e) => setForm({ ...form, duration_days: e.target.value ? Number(e.target.value) : null })}
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
                            onChange={(e) => setForm({ ...form, start_date: e.target.value || null })}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            End Date - Optional
                        </label>
                        <input
                            type="date"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.end_date || ""}
                            onChange={(e) => setForm({ ...form, end_date: e.target.value || null })}
                        />
                    </div>
                </div>

                <div className="flex justify-between">
                    {goal && (
                        <button
                            type="button"
                            onClick={handleDelete}
                            disabled={saving}
                            className="inline-flex justify-center py-2 px-4 border border-red-300 shadow-sm text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                        >
                            Delete Goal
                        </button>
                    )}
                    <button
                        type="submit"
                        disabled={saving}
                        className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 ml-auto"
                    >
                        {saving ? "Saving..." : goal ? "Update Goal" : "Create Goal"}
                    </button>
                </div>
            </form>

            {goal && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-blue-900 mb-2">Current Goal</h3>
                    <dl className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2">
                        <div>
                            <dt className="text-sm text-blue-700">Type:</dt>
                            <dd className="text-sm font-medium text-blue-900 capitalize">{goal.goal_type}</dd>
                        </div>
                        {goal.target_delta_kg && (
                            <div>
                                <dt className="text-sm text-blue-700">Target Change:</dt>
                                <dd className="text-sm font-medium text-blue-900">{goal.target_delta_kg} kg</dd>
                            </div>
                        )}
                        {goal.duration_days && (
                            <div>
                                <dt className="text-sm text-blue-700">Duration:</dt>
                                <dd className="text-sm font-medium text-blue-900">{goal.duration_days} days</dd>
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
                            <p className="mt-1 text-sm text-gray-500">Track your weight to see if you're hitting your target.</p>
                        </div>

                        <form onSubmit={handleLogWeight} className="flex gap-2 items-center">
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
                            targetWeight={
                                goal.target_delta_kg
                                    // if lose, target is conceptually lower. the chart expects absolute values
                                    // we can just optionally pass target weight if we knew start weight. 
                                    // we omit it here as we don't store "starting weight" on the goal itself easily without the first log.
                                    ? null
                                    : null
                            }
                        />
                    </div>

                    {logs.length > 0 && (
                        <div className="mt-4">
                            <h3 className="text-sm font-medium text-gray-900 mb-3">Recent Logs</h3>
                            <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 rounded-lg">
                                <table className="min-w-full divide-y divide-gray-300">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900">Date</th>
                                            <th scope="col" className="px-3 py-3.5 text-right text-sm font-semibold text-gray-900">Weight</th>
                                            <th scope="col" className="px-3 py-3.5 text-right text-sm font-semibold text-gray-900">Due Target (Delta)</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-200 bg-white">
                                        {[...logs].reverse().slice(0, 5).map((log) => (
                                            <tr key={log.id}>
                                                <td className="whitespace-nowrap py-3 pl-4 pr-3 text-sm text-gray-500">
                                                    {new Date(log.date).toLocaleDateString()} {new Date(log.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
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
