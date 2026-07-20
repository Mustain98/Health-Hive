"use client";

import { useEffect, useState, FormEvent } from "react";
import { apiFetch } from "@/lib/api";
import { formatGoalDetail } from "@/lib/format";
import { LogHistoryTable } from "@/components/ui/LogHistoryTable";
import type { DailyGoalRead, DailyGoalType, DailyLogForm, DailyLogHistoryDay } from "@/lib/types";

const TYPE_META: Record<DailyGoalType, { label: string; unit: string; icon: string }> = {
    exercise: { label: "Exercise", unit: "reps", icon: "🏋️" },
    calorie_burn: { label: "Calorie burn", unit: "kcal", icon: "🔥" },
    intake: { label: "Intake", unit: "g", icon: "🥗" },
    steps: { label: "Steps", unit: "steps", icon: "👟" },
    custom: { label: "Custom", unit: "", icon: "⭐" },
};

// Client-local calendar day (YYYY-MM-DD) — decision 10.
const localDate = () => new Date().toLocaleDateString("en-CA");

// Backend convention: Mon=0 … Sun=6; null/[] = every day.
const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const formatDays = (days: number[] | null | undefined) =>
    !days || days.length === 0 ? "Every day" : [...days].sort((a, b) => a - b).map((d) => DAY_LABELS[d]).join(", ");

export default function DailyGoalsPage() {
    const [goals, setGoals] = useState<DailyGoalRead[]>([]);
    const [today, setToday] = useState<DailyLogForm | null>(null);
    const [loading, setLoading] = useState(true);
    const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

    // create form
    const [goalType, setGoalType] = useState<DailyGoalType>("exercise");
    const [name, setName] = useState("");
    const [targetValue, setTargetValue] = useState("");
    const [unit, setUnit] = useState("reps");
    const [detail, setDetail] = useState(""); // free-form -> attributes.note
    const [daysOfWeek, setDaysOfWeek] = useState<number[]>([]); // empty = every day
    const [creating, setCreating] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);

    // log form local state
    const [logState, setLogState] = useState<Record<string, { completed: boolean; value: string }>>({});
    const [caloriesIn, setCaloriesIn] = useState("");
    const [caloriesOut, setCaloriesOut] = useState("");
    const [savingLog, setSavingLog] = useState(false);
    const [logDate, setLogDate] = useState(localDate()); // which day is being logged (backfill allowed)
    const [history, setHistory] = useState<DailyLogHistoryDay[]>([]);

    async function loadAll(day: string = logDate) {
        try {
            const [g, t, h] = await Promise.all([
                apiFetch<DailyGoalRead[]>("/api/daily-goals/me"),
                apiFetch<DailyLogForm>(`/api/daily-goals/today?date=${day}`),
                apiFetch<DailyLogHistoryDay[]>("/api/daily-goals/history"),
            ]);
            setGoals(g);
            setToday(t);
            setHistory(h);
            const ls: Record<string, { completed: boolean; value: string }> = {};
            t.daily_goals.forEach((dg) => { ls[dg.id] = { completed: dg.completed, value: dg.value != null ? String(dg.value) : "" }; });
            setLogState(ls);
            setCaloriesIn(t.calories_in != null ? String(t.calories_in) : "");
            setCaloriesOut(t.calories_out != null ? String(t.calories_out) : "");
        } catch (err: any) {
            setMessage({ text: err.message, type: "error" });
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => { loadAll(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

    function changeLogDate(day: string) {
        if (!day) return;
        setLogDate(day);
        loadAll(day);
    }

    function startEdit(g: DailyGoalRead) {
        setEditingId(g.id);
        setGoalType(g.goal_type);
        setName(g.name);
        setTargetValue(g.target_value != null ? String(g.target_value) : "");
        setUnit(g.unit || "");
        setDetail(g.attributes?.note || "");
        setDaysOfWeek(g.days_of_week ?? []);
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function cancelEdit() {
        setEditingId(null);
        setName(""); setTargetValue(""); setDetail("");
        setDaysOfWeek([]);
    }

    function toggleDay(d: number) {
        setDaysOfWeek((days) => (days.includes(d) ? days.filter((x) => x !== d) : [...days, d]));
    }

    async function handleCreate(e: FormEvent) {
        e.preventDefault();
        if (!name.trim()) return;
        setCreating(true);
        setMessage(null);
        const attributes: Record<string, any> = {};
        if (detail.trim()) attributes.note = detail.trim();
        if (goalType === "exercise" && name.trim()) attributes.exercise = name.trim();
        const body = {
            goal_type: goalType,
            name: name.trim(),
            target_value: targetValue ? Number(targetValue) : null,
            unit: unit || null,
            days_of_week: daysOfWeek.length ? daysOfWeek : null,
            attributes,
        };
        try {
            if (editingId) {
                await apiFetch(`/api/daily-goals/${editingId}`, { method: "PATCH", body });
                setMessage({ text: "Daily goal updated ✅", type: "success" });
            } else {
                await apiFetch("/api/daily-goals/me", { method: "POST", body: { ...body, active: true } });
                setMessage({ text: "Daily goal added ✅", type: "success" });
            }
            setEditingId(null);
            setName(""); setTargetValue(""); setDetail("");
            setDaysOfWeek([]);
            await loadAll();
        } catch (err: any) {
            setMessage({ text: err.message, type: "error" });
        } finally {
            setCreating(false);
        }
    }

    async function toggleActive(g: DailyGoalRead) {
        try {
            await apiFetch(`/api/daily-goals/${g.id}/${g.active ? "deactivate" : "activate"}`, { method: "PATCH" });
            await loadAll();
        } catch (err: any) {
            setMessage({ text: err.message, type: "error" });
        }
    }

    async function remove(g: DailyGoalRead) {
        if (!confirm(`Delete "${g.name}"?`)) return;
        try {
            await apiFetch(`/api/daily-goals/${g.id}`, { method: "DELETE" });
            await loadAll();
        } catch (err: any) {
            setMessage({ text: err.message, type: "error" });
        }
    }

    async function submitLog(e: FormEvent) {
        e.preventDefault();
        setSavingLog(true);
        setMessage(null);
        try {
            const completions = Object.entries(logState).map(([id, v]) => ({
                daily_goal_id: id,
                completed: v.completed,
                value: v.value ? Number(v.value) : null,
            }));
            const res = await apiFetch<DailyLogForm>("/api/daily-goals/log", {
                method: "POST",
                body: {
                    date: logDate,
                    completions,
                    calories_in: caloriesIn ? Number(caloriesIn) : null,
                    calories_out: caloriesOut ? Number(caloriesOut) : null,
                },
            });
            setToday((t) => (t ? { ...t, ...res } : t));
            setHistory(await apiFetch<DailyLogHistoryDay[]>("/api/daily-goals/history"));
            setMessage({ text: `Logged ${logDate === localDate() ? "today" : logDate} ✅`, type: "success" });
        } catch (err: any) {
            setMessage({ text: err.message, type: "error" });
        } finally {
            setSavingLog(false);
        }
    }

    const deficit = (caloriesIn && caloriesOut) ? Number(caloriesIn) - Number(caloriesOut) : today?.deficit_surplus ?? null;

    if (loading) return <div className="text-center py-12 text-gray-500">Loading…</div>;

    return (
        <div className="max-w-3xl mx-auto space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">✅ Daily Goals</h1>
                <p className="text-gray-500 mt-1">Habits that drive your milestone — logged daily.</p>
            </div>

            {message && (
                <div className={`px-4 py-3 rounded-xl border text-sm ${message.type === "success" ? "bg-green-50 text-green-800 border-green-200" : "bg-red-50 text-red-800 border-red-200"}`}>
                    {message.text}
                </div>
            )}

            {/* Daily log form (today or a missed previous day) */}
            <form onSubmit={submitLog} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4">
                <div className="flex items-center justify-between flex-wrap gap-2">
                    <h2 className="text-lg font-semibold text-gray-900">
                        {logDate === localDate() ? "Today's log" : `Log for ${logDate}`}
                    </h2>
                    <div className="flex items-center gap-2">
                        <label className="text-xs font-medium text-gray-500">Day</label>
                        <input
                            type="date"
                            value={logDate}
                            max={localDate()}
                            onChange={(e) => changeLogDate(e.target.value)}
                            className="rounded-md border border-gray-300 px-2 py-1 text-sm"
                        />
                        {logDate !== localDate() && (
                            <button type="button" onClick={() => changeLogDate(localDate())} className="text-xs text-emerald-600 font-medium hover:text-emerald-700">
                                back to today
                            </button>
                        )}
                    </div>
                </div>
                {today && today.daily_goals.length === 0 ? (
                    <p className="text-sm text-gray-400">No active daily goals yet — add one below.</p>
                ) : (
                    <div className="space-y-2">
                        {today?.daily_goals.map((dg) => (
                            <div key={dg.id} className="flex items-center gap-3 p-2 rounded-lg border border-gray-100">
                                <input
                                    type="checkbox"
                                    checked={logState[dg.id]?.completed || false}
                                    onChange={(e) => setLogState((s) => ({ ...s, [dg.id]: { ...s[dg.id], completed: e.target.checked } }))}
                                    className="h-5 w-5 rounded text-emerald-600"
                                />
                                <div className="flex-1">
                                    <p className="text-sm font-medium text-gray-800">{TYPE_META[dg.goal_type].icon} {dg.name}</p>
                                    <div className="flex items-center gap-2 mt-0.5">
                                        {formatGoalDetail(dg) && <span className="text-xs text-gray-400 font-medium">target {formatGoalDetail(dg)}</span>}
                                        <span className="text-[10px] uppercase tracking-wider font-bold text-gray-300">· {formatDays(dg.days_of_week)}</span>
                                    </div>
                                </div>
                                <input
                                    type="number"
                                    placeholder="actual"
                                    value={logState[dg.id]?.value || ""}
                                    onChange={(e) => setLogState((s) => ({ ...s, [dg.id]: { ...s[dg.id], value: e.target.value } }))}
                                    className="w-24 rounded-md border border-gray-300 px-2 py-1 text-sm"
                                />
                            </div>
                        ))}
                    </div>
                )}

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2 border-t border-gray-100">
                    <div>
                        <label className="block text-xs font-medium text-gray-500">Calories in</label>
                        <input type="number" value={caloriesIn} onChange={(e) => setCaloriesIn(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1 text-sm" />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500">Calories out</label>
                        <input type="number" value={caloriesOut} onChange={(e) => setCaloriesOut(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1 text-sm" />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500">Deficit / surplus</label>
                        <p className={`mt-1 text-sm font-semibold ${deficit == null ? "text-gray-400" : deficit < 0 ? "text-emerald-600" : "text-red-600"}`}>
                            {deficit == null ? "—" : `${deficit > 0 ? "+" : ""}${deficit} kcal`}
                        </p>
                    </div>
                </div>

                <button type="submit" disabled={savingLog} className="px-4 py-2 text-sm font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50">
                    {savingLog ? "Saving…" : logDate === localDate() ? "Save today's log" : `Save log for ${logDate}`}
                </button>
            </form>

            {/* Add / edit a daily goal */}
            <form onSubmit={handleCreate} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4">
                <h2 className="text-lg font-semibold text-gray-900">{editingId ? "Edit daily goal" : "Add a daily goal"}</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label className="block text-xs font-medium text-gray-500">Type</label>
                        <select
                            value={goalType}
                            onChange={(e) => { const t = e.target.value as DailyGoalType; setGoalType(t); setUnit(TYPE_META[t].unit); }}
                            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                        >
                            {(Object.keys(TYPE_META) as DailyGoalType[]).map((t) => (
                                <option key={t} value={t}>{TYPE_META[t].icon} {TYPE_META[t].label}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500">Name</label>
                        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. 30 pushups" className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500">Target</label>
                        <input type="number" value={targetValue} onChange={(e) => setTargetValue(e.target.value)} placeholder="e.g. 30" className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500">Unit</label>
                        <input value={unit} onChange={(e) => setUnit(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
                    </div>
                </div>
                <div>
                    <label className="block text-xs font-medium text-gray-500">Days <span className="font-normal text-gray-400">(none selected = every day)</span></label>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                        {DAY_LABELS.map((label, d) => (
                            <button
                                key={label}
                                type="button"
                                onClick={() => toggleDay(d)}
                                className={`px-2.5 py-1 text-xs font-medium rounded-full border ${daysOfWeek.includes(d) ? "bg-emerald-600 text-white border-emerald-600" : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"}`}
                            >
                                {label}
                            </button>
                        ))}
                    </div>
                </div>
                <div>
                    <label className="block text-xs font-medium text-gray-500">Details (optional)</label>
                    <input value={detail} onChange={(e) => setDetail(e.target.value)} placeholder="notes, e.g. after breakfast" className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
                </div>
                <div className="flex gap-2">
                    <button type="submit" disabled={creating || !name.trim()} className="px-4 py-2 text-sm font-semibold rounded-lg bg-orange-500 text-white hover:bg-orange-600 disabled:opacity-50">
                        {creating ? "Saving…" : editingId ? "Save changes" : "Add daily goal"}
                    </button>
                    {editingId && (
                        <button type="button" onClick={cancelEdit} className="px-4 py-2 text-sm font-semibold rounded-lg bg-white text-gray-600 border border-gray-300 hover:bg-gray-50">
                            Cancel
                        </button>
                    )}
                </div>
            </form>

            {/* All daily goals */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">All daily goals</h2>
                {goals.length === 0 ? (
                    <p className="text-sm text-gray-400">None yet.</p>
                ) : (
                    <div className="space-y-2">
                        {goals.map((g) => (
                            <div key={g.id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-100">
                                <span className="text-xl">{TYPE_META[g.goal_type].icon}</span>
                                <div className="flex-1">
                                    <p className="text-sm font-medium text-gray-800">{g.name}</p>
                                    <p className="text-xs text-gray-400">
                                        {TYPE_META[g.goal_type].label}{formatGoalDetail(g) ? ` · ${formatGoalDetail(g)}` : ""}
                                        {` · ${formatDays(g.days_of_week)}`}
                                        {g.active ? "" : " · inactive"}
                                    </p>
                                </div>
                                <button onClick={() => startEdit(g)} className="text-xs px-3 py-1.5 rounded-lg font-medium bg-white border border-gray-200 text-gray-600 hover:bg-gray-50">
                                    Edit
                                </button>
                                <button onClick={() => toggleActive(g)} className={`text-xs px-3 py-1.5 rounded-lg font-medium ${g.active ? "bg-gray-100 text-gray-600 hover:bg-gray-200" : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"}`}>
                                    {g.active ? "Deactivate" : "Activate"}
                                </button>
                                <button onClick={() => remove(g)} className="text-xs px-3 py-1.5 rounded-lg font-medium bg-white border border-red-200 text-red-600 hover:bg-red-50">
                                    Delete
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Log history */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">History (last 30 days)</h2>
                <LogHistoryTable history={history} />
            </div>
        </div>
    );
}
