"use client";

import { useEffect, useState, FormEvent } from "react";
import { apiFetch } from "@/lib/api";
import type { GoalRead, GoalUpsert, GoalType, GoalLogRead } from "@/lib/types";
import { GoalTrackerChart } from "@/components/ui/GoalTrackerChart";

export default function GoalPage() {
    const [goals, setGoals] = useState<GoalRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    // Start date change
    const [newStartDate, setNewStartDate] = useState<string>("");
    const [changingDate, setChangingDate] = useState(false);
    const [showDateForm, setShowDateForm] = useState(false);

    // Form state for creating custom goal
    const [form, setForm] = useState<GoalUpsert>({
        goal_type: "lose",
        target_weight: null,
        duration_days: null,
        start_date: null,
        end_date: null,
    });

    // Tracking state
    const [logs, setLogs] = useState<GoalLogRead[]>([]);
    const [weightInput, setWeightInput] = useState<string>("");
    const [loggingWeight, setLoggingWeight] = useState(false);

    useEffect(() => {
        loadGoals();
    }, []);

    async function loadGoals() {
        try {
            const data = await apiFetch<GoalRead[]>("/api/goal/all");
            setGoals(data);

            const activeGoal = data.find(g => g.active);
            if (activeGoal) {
                try {
                    const logsData = await apiFetch<GoalLogRead[]>(`/api/goal/${activeGoal.id}/logs`);
                    setLogs(logsData);
                } catch (e) {
                    console.error("Failed to load goal tracking logs:", e);
                }
            }
        } catch (error: any) {
            console.error("Failed to load goals:", error);
        } finally {
            setLoading(false);
        }
    }

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

    async function handleAdopt(id: string) {
        if (!confirm("Are you sure you want to adopt this goal? It will deactivate your current one.")) return;
        setSaving(true);
        setMessage(null);
        try {
            await apiFetch(`/api/goal/${id}/activate`, {
                method: "PUT",
            });
            await loadGoals();
            setMessage("Goal adopted successfully.");
            setForm({
                goal_type: "lose",
                target_weight: null,
                duration_days: null,
                start_date: null,
                end_date: null,
            });
        } catch (e: any) {
            setMessage(`Failed to adopt goal: ${e.message}`);
        } finally {
            setSaving(false);
        }
    }

    async function handleCreate(e: FormEvent) {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        // Validation
        if (form.goal_type !== "maintain" && (!form.target_weight || form.target_weight <= 0)) {
            setMessage("Error: Target weight must be greater than 0 for lose/gain goals");
            setSaving(false);
            return;
        }

        if (form.goal_type === "maintain") {
            form.target_weight = null;
        }

        try {
            await apiFetch("/api/goal/me", {
                method: "PUT", // Endpoint creates and sets active
                body: form,
            });
            await loadGoals();
            setMessage("New Goal created and activated.");
            setForm({
                goal_type: "lose",
                target_weight: null,
                duration_days: null,
                start_date: null,
                end_date: null,
            });
        } catch (error: any) {
            setMessage(`Failed to create goal: ${error.message}`);
        } finally {
            setSaving(false);
        }
    }

    async function handleDelete() {
        if (!confirm("Are you sure you want to deactivate your current goal?")) return;

        setSaving(true);
        setMessage(null);

        try {
            await apiFetch("/api/goal/me", { method: "DELETE" });
            await loadGoals();
            setMessage("Goal deactivated successfully");
            setLogs([]);
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setSaving(false);
        }
    }

    async function handleChangeDate(e: FormEvent) {
        e.preventDefault();
        if (!activeGoal || !newStartDate) return;
        setChangingDate(true);
        setMessage(null);
        try {
            await apiFetch(`/api/goal/${activeGoal.id}/change-date`, {
                method: "PATCH",
                body: { new_start_date: newStartDate },
            });
            await loadGoals();
            setMessage("Start date updated. End date recalculated automatically.");
            setShowDateForm(false);
            setNewStartDate("");
        } catch (error: any) {
            setMessage(`Failed to update date: ${error.message}`);
        } finally {
            setChangingDate(false);
        }
    }

    const activeGoal = goals.find((g) => g.active);
    const otherGoals = goals.filter((g) => !g.active);

    if (loading) {
        return <div className="p-8 text-center text-gray-500">Loading goals...</div>;
    }

    return (
        <div className="max-w-4xl mx-auto p-4 md:p-8 space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900 mb-2">My Goal</h1>
                <p className="text-gray-600">
                    Set and track your weight goals manually
                </p>
            </div>

            {message && (
                <div className={`rounded-xl px-4 py-3 border ${message.includes("Error") || message.includes("Failed") ? "bg-red-50 text-red-800 border-red-200" : "bg-blue-50 text-blue-800 border-blue-200"}`}>
                    <p className="text-sm font-medium">{message}</p>
                </div>
            )}

            {/* Active Goal Section */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 flex gap-2">
                    {activeGoal && (
                        <button
                            type="button"
                            onClick={handleDelete}
                            disabled={saving}
                            className="text-xs font-medium px-3 py-1 bg-red-50 text-red-600 rounded-md hover:bg-red-100"
                        >
                            Deactivate
                        </button>
                    )}
                    <span className="bg-green-100 text-green-700 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                        Active
                    </span>
                </div>
                <h2 className="text-xl font-semibold mb-4 text-gray-800">Current Goal</h2>

                {activeGoal ? (
                    <div>
                        <div className="flex flex-wrap gap-8 mb-6">
                            <div>
                                <p className="text-sm text-gray-500 font-medium tracking-wide uppercase mb-1">Type</p>
                                <p className="text-2xl font-bold capitalize text-gray-800">{activeGoal.goal_type}</p>
                            </div>
                            {activeGoal.target_weight && (
                                <div>
                                    <p className="text-sm text-gray-500 font-medium tracking-wide uppercase mb-1">Target Weight</p>
                                    <p className="text-2xl font-bold text-gray-800">{activeGoal.target_weight} <span className="text-base text-gray-500 font-normal">kg</span></p>
                                </div>
                            )}
                            {activeGoal.initial_weight && (
                                <div>
                                    <p className="text-sm text-gray-500 font-medium tracking-wide uppercase mb-1">Initial Weight</p>
                                    <p className="text-2xl font-bold text-gray-800">{activeGoal.initial_weight} <span className="text-base text-gray-500 font-normal">kg</span></p>
                                </div>
                            )}
                            {activeGoal.duration_days && (
                                <div>
                                    <p className="text-sm text-gray-500 font-medium tracking-wide uppercase mb-1">Duration</p>
                                    <p className="text-2xl font-bold text-gray-800">{activeGoal.duration_days} <span className="text-base text-gray-500 font-normal">days</span></p>
                                </div>
                            )}
                            {activeGoal.start_date && (
                                <div>
                                    <p className="text-sm text-gray-500 font-medium tracking-wide uppercase mb-1">Start Date</p>
                                    <p className="text-lg font-bold text-gray-800">{new Date(activeGoal.start_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</p>
                                </div>
                            )}
                            {activeGoal.end_date && (
                                <div>
                                    <p className="text-sm text-gray-500 font-medium tracking-wide uppercase mb-1">End Date</p>
                                    <p className="text-lg font-bold text-gray-800">{new Date(activeGoal.end_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</p>
                                </div>
                            )}
                        </div>

                        {activeGoal.created_by !== activeGoal.created_for && activeGoal.created_by_name && (
                            <div className="mb-4 p-3 bg-blue-50/50 border border-blue-100 rounded-lg inline-block">
                                <p className="text-xs text-blue-600 font-bold uppercase tracking-wider mb-1">Consultant Plan</p>
                                <div className="text-sm">
                                    <div className="font-medium text-gray-800">👤 {activeGoal.created_by_name}</div>
                                </div>
                            </div>
                        )}

                        {/* Change Start Date */}
                        {activeGoal.duration_days && (
                            <div className="mb-6">
                                <button
                                    type="button"
                                    onClick={() => setShowDateForm(!showDateForm)}
                                    className="text-xs font-medium text-indigo-600 hover:text-indigo-800 underline"
                                >
                                    {showDateForm ? "Cancel" : "Change start date"}
                                </button>
                                {showDateForm && (
                                    <form onSubmit={handleChangeDate} className="mt-3 flex flex-wrap items-end gap-3 bg-gray-50 border border-gray-200 rounded-xl p-4">
                                        <div>
                                            <label className="block text-xs font-medium text-gray-600 mb-1">New Start Date</label>
                                            <input
                                                type="date"
                                                required
                                                value={newStartDate}
                                                onChange={e => setNewStartDate(e.target.value)}
                                                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                                            />
                                        </div>
                                        <div className="text-xs text-gray-500">
                                            End date will be recalculated automatically<br />from duration ({activeGoal.duration_days} days).
                                        </div>
                                        <button
                                            type="submit"
                                            disabled={changingDate || !newStartDate}
                                            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                                        >
                                            {changingDate ? "Saving..." : "Update"}
                                        </button>
                                    </form>
                                )}
                            </div>
                        )}

                        {/* Goal Tracker Section */}
                        <div className="mt-8 pt-6 border-t border-gray-100">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                                <div>
                                    <h3 className="text-lg font-bold text-gray-900">Goal Progress</h3>
                                    <p className="mt-1 text-sm text-gray-500">
                                        Track your weight to see if you&apos;re hitting your target.
                                    </p>
                                </div>

                                <form onSubmit={handleLogWeight} className="flex gap-2 items-center">
                                    <input
                                        type="number" step="0.1" required
                                        value={weightInput} onChange={(e) => setWeightInput(e.target.value)}
                                        placeholder="Today's Weight (kg)"
                                        className="block w-40 rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                    />
                                    <button
                                        type="submit" disabled={loggingWeight || !weightInput}
                                        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 transition-colors shadow-sm"
                                    >
                                        {loggingWeight ? "..." : "Log"}
                                    </button>
                                </form>
                            </div>

                            <div className="border border-gray-100 rounded-xl p-4 bg-gray-50/50">
                                <GoalTrackerChart
                                    logs={logs}
                                    goalType={activeGoal.goal_type}
                                    targetWeight={activeGoal.target_weight ?? null}
                                    initialWeight={activeGoal.initial_weight ?? null}
                                />
                            </div>

                            {logs.length > 0 && (
                                <div className="mt-6">
                                    <h4 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wider">
                                        Recent Logs
                                    </h4>
                                    <div className="overflow-hidden shadow-sm ring-1 ring-gray-200 rounded-xl">
                                        <table className="min-w-full divide-y divide-gray-200">
                                            <thead className="bg-gray-50">
                                                <tr>
                                                    <th scope="col" className="py-3 pl-4 pr-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
                                                    <th scope="col" className="px-3 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Weight</th>
                                                    <th scope="col" className="px-3 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Due Target (Delta)</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-100 bg-white">
                                                {[...logs]
                                                    .reverse()
                                                    .slice(0, 5)
                                                    .map((log) => (
                                                        <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                                                            <td className="whitespace-nowrap py-3 pl-4 pr-3 text-sm text-gray-600">
                                                                {new Date(log.date).toLocaleDateString()}{" "}
                                                                <span className="text-gray-400 text-xs ml-1">
                                                                    {new Date(log.date).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                                                </span>
                                                            </td>
                                                            <td className="whitespace-nowrap px-3 py-3 text-sm text-gray-900 text-right font-semibold">
                                                                {log.weight} <span className="text-gray-400 font-normal">kg</span>
                                                            </td>
                                                            <td className="whitespace-nowrap px-3 py-3 text-sm text-gray-500 text-right font-medium">
                                                                {log.due_terget.toFixed(2)} <span className="text-gray-400 font-normal">kg</span>
                                                            </td>
                                                        </tr>
                                                    ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}
                        </div>

                    </div>
                ) : (
                    <p className="text-gray-500">You don&apos;t have an active goal. Create or adopt one below.</p>
                )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 pt-4">

                {/* Suggested / Previous Goals */}
                <div>
                    <h2 className="text-xl font-semibold mb-4 text-gray-800">Suggested & Past Goals</h2>
                    {otherGoals.length === 0 ? (
                        <p className="text-gray-500 text-sm italic">No other goals found.</p>
                    ) : (
                        <div className="space-y-4">
                            {otherGoals.map(g => {
                                const isSuggestion = g.created_by !== g.created_for;
                                return (
                                    <div key={g.id} className={`p-5 rounded-2xl border ${isSuggestion ? 'border-blue-200 bg-blue-50/50' : 'border-gray-200 bg-white'}`}>
                                        <div className="flex justify-between items-start mb-3">
                                            <div>
                                                {isSuggestion && <span className="text-[10px] font-bold text-blue-600 uppercase tracking-widest block mb-1.5">Consultant Suggestion</span>}
                                                <h3 className="font-bold text-gray-900 text-lg capitalize">{g.goal_type} Weight</h3>
                                                {isSuggestion && g.created_by_name && (
                                                    <div className="text-xs text-blue-700 mt-1">
                                                        👤 <span className="font-medium">{g.created_by_name}</span>
                                                    </div>
                                                )}
                                            </div>
                                            <button
                                                onClick={() => handleAdopt(g.id)}
                                                disabled={saving}
                                                className={`text-sm px-4 py-2 rounded-lg font-medium transition-colors ${isSuggestion
                                                    ? "bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300 shadow-sm"
                                                    : "bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:bg-gray-50"
                                                    }`}
                                            >
                                                Adopt
                                            </button>
                                        </div>

                                        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm mt-4 bg-white/60 rounded-lg p-3 border border-gray-100/50 shadow-sm">
                                            {g.target_weight && (
                                                <div><span className="text-gray-500">Target:</span> <span className="font-semibold text-gray-800">{g.target_weight} kg</span></div>
                                            )}
                                            {g.duration_days && (
                                                <div><span className="text-gray-500">Duration:</span> <span className="font-semibold text-gray-800">{g.duration_days} days</span></div>
                                            )}
                                            <div className="col-span-2 text-xs text-gray-400 mt-1">Created {new Date(g.created_at).toLocaleDateString()}</div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Create Custom Goal */}
                <div>
                    <h2 className="text-xl font-semibold mb-4 text-gray-800">Create New Goal</h2>
                    <form onSubmit={handleCreate} className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm space-y-5">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Goal Type</label>
                            <select
                                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2.5 border"
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
                                <label className="block text-sm font-medium text-gray-700 mb-1">Target Weight (kg)</label>
                                <input
                                    type="number" step="0.1" min="0.1"
                                    className="w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2.5 border"
                                    value={form.target_weight ?? ""}
                                    onChange={(e) => setForm({ ...form, target_weight: e.target.value ? Number(e.target.value) : null })}
                                    placeholder={form.goal_type === "lose" ? "e.g., 70" : "e.g., 80"}
                                />
                            </div>
                        )}

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Duration (days) <span className="font-normal text-gray-400">- Optional</span></label>
                            <input
                                type="number" min="1"
                                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2.5 border"
                                value={form.duration_days ?? ""}
                                onChange={(e) => setForm({ ...form, duration_days: e.target.value ? Number(e.target.value) : null })}
                                placeholder="e.g., 30"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={saving}
                            className="w-full bg-gray-900 text-white font-medium py-2.5 rounded-xl hover:bg-gray-800 focus:ring-4 focus:ring-gray-200 transition-all active:scale-[0.98] disabled:opacity-50 mt-4 shadow-sm"
                        >
                            {saving ? "Creating..." : "Create & Activate Goal"}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
