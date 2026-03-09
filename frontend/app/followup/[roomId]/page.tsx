"use client";

import { useEffect, useRef, useState, FormEvent } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/components/guards/AuthGuard";
import type {
    FollowUpMessage,
    TimeProposal,
    AppointmentRead,
    FollowUpRoomRead,
    PatientSummaryRead,
    GoalLogRead,
} from "@/lib/types";
import { GoalTrackerChart } from "@/components/ui/GoalTrackerChart";

const WS_BASE =
    process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, "ws") || "ws://127.0.0.1:8000";

function fixDate(d: string | null | undefined): string | null | undefined {
    return d && typeof d === "string" && !d.endsWith("Z") ? d + "Z" : d;
}
function fixAppt(a: AppointmentRead): AppointmentRead {
    return { ...a, scheduled_start_at: fixDate(a.scheduled_start_at) as string, scheduled_end_at: fixDate(a.scheduled_end_at) as string };
}
function fixProposal(p: TimeProposal): TimeProposal {
    return { ...p, start_at: fixDate(p.start_at) as string, end_at: fixDate(p.end_at) as string };
}

type Tab = "health" | "sessions" | "chat";

export default function UserFollowUpRoomPage() {
    const { roomId } = useParams<{ roomId: string }>();
    const { user: me } = useAuth();

    const [tab, setTab] = useState<Tab>("health");
    const [room, setRoom] = useState<FollowUpRoomRead | null>(null);
    const [sessions, setSessions] = useState<AppointmentRead[]>([]);
    const [messages, setMessages] = useState<FollowUpMessage[]>([]);
    const [proposals, setProposals] = useState<TimeProposal[]>([]);
    const [summary, setSummary] = useState<PatientSummaryRead | null>(null);

    // Goal tracking
    const [weightInput, setWeightInput] = useState("");
    const [loggingWeight, setLoggingWeight] = useState(false);

    const [newMsg, setNewMsg] = useState("");
    const [sending, setSending] = useState(false);
    const [cancelling, setCancelling] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const msgEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        loadAll();
    }, [roomId]);

    useEffect(() => {
        if (!roomId) return;
        const ws = new WebSocket(`${WS_BASE}/api/followup/ws/${roomId}`);
        wsRef.current = ws;
        ws.onmessage = (e) => {
            try {
                const incoming = JSON.parse(e.data) as FollowUpMessage;
                setMessages((prev) =>
                    prev.some((m) => m.id === incoming.id) ? prev : [...prev, incoming]
                );
            } catch { /* ignore */ }
        };
        return () => ws.close();
    }, [roomId]);

    useEffect(() => {
        msgEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    async function loadAll() {
        setLoading(true);
        try {
            const [roomData, sessionsData, msgs, props, sumData] = await Promise.all([
                apiFetch<FollowUpRoomRead>(`/api/followup/rooms/${roomId}`),
                apiFetch<AppointmentRead[]>(`/api/followup/rooms/${roomId}/sessions`),
                apiFetch<FollowUpMessage[]>(`/api/followup/rooms/${roomId}/messages`),
                apiFetch<TimeProposal[]>(`/api/followup/rooms/${roomId}/proposals`),
                apiFetch<PatientSummaryRead>(`/api/followup/rooms/${roomId}/my-summary`).catch(() => null),
            ]);
            if (roomData.reactivated_at) roomData.reactivated_at = fixDate(roomData.reactivated_at) as string;
            setRoom(roomData);
            setSessions(sessionsData.map(fixAppt));
            setMessages(msgs);
            setProposals(props.map(fixProposal));
            if (sumData) setSummary(sumData);
        } catch (e: any) {
            setError(e.message || "Failed to load room");
        } finally {
            setLoading(false);
        }
    }

    async function refreshAll() {
        const [msgs, props, sess] = await Promise.all([
            apiFetch<FollowUpMessage[]>(`/api/followup/rooms/${roomId}/messages`),
            apiFetch<TimeProposal[]>(`/api/followup/rooms/${roomId}/proposals`),
            apiFetch<AppointmentRead[]>(`/api/followup/rooms/${roomId}/sessions`),
        ]);
        setMessages(msgs);
        setProposals(props.map(fixProposal));
        setSessions(sess.map(fixAppt));
    }

    async function handleSend(e: FormEvent) {
        e.preventDefault();
        if (!newMsg.trim() || sending) return;
        setSending(true);
        try {
            const saved = await apiFetch<FollowUpMessage>(`/api/followup/rooms/${roomId}/messages`, {
                method: "POST",
                body: { message: newMsg },
            });
            setMessages((prev) => (prev.some((m) => m.id === saved.id) ? prev : [...prev, saved]));
            wsRef.current?.send(JSON.stringify(saved));
            setNewMsg("");
        } catch (e: any) {
            setError(e.message);
        } finally {
            setSending(false);
        }
    }

    async function handleLogWeight(e: FormEvent) {
        e.preventDefault();
        if (!weightInput || isNaN(Number(weightInput)) || !summary) return;

        setLoggingWeight(true);
        try {
            const newLog = await apiFetch<GoalLogRead>("/api/goal/log", {
                method: "POST",
                body: { weight: Number(weightInput) },
            });
            // Update summary with new log
            setSummary(prev => prev ? { ...prev, logs: [...prev.logs, newLog] } : prev);
            setWeightInput("");
        } catch (error: any) {
            alert(error.message);
        } finally {
            setLoggingWeight(false);
        }
    }

    async function handleProposalAction(proposalId: string, action: "accept" | "reject") {
        try {
            await apiFetch(`/api/followup/proposals/${proposalId}/${action}`, { method: "POST" });
            await refreshAll();
            if (action === "accept") setTab("sessions"); // show the new session
        } catch (e: any) {
            alert(e.message);
        }
    }

    async function handleCancel() {
        if (!confirm("Cancel this follow-up?")) return;
        setCancelling(true);
        try {
            const updated = await apiFetch<FollowUpRoomRead>(`/api/followup/rooms/${roomId}/cancel`, {
                method: "POST",
            });
            setRoom(updated);
        } catch (e: any) {
            alert(e.message);
        } finally {
            setCancelling(false);
        }
    }

    if (loading) return <div className="text-center py-12 text-gray-500">Loading…</div>;
    if (error) return <div className="text-center py-12 text-red-500">{error}</div>;
    if (!room) return null;

    const isActive = room.status === "active";
    const pendingProposals = proposals.filter((p) => p.status === "pending");

    // Session split for reactivated rooms
    const reactivatedAt = room.reactivated_at ? new Date(room.reactivated_at) : null;
    const archivedSessions = reactivatedAt
        ? sessions.filter((s) => new Date(s.scheduled_start_at) < reactivatedAt)
        : [];
    const currentSessions = reactivatedAt
        ? sessions.filter((s) => new Date(s.scheduled_start_at) >= reactivatedAt)
        : sessions;

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">
                        Follow-up with {room.other_party_name ?? "Consultant"}
                    </h1>
                    {room.other_party_email && (
                        <p className="text-sm text-gray-500">{room.other_party_email}</p>
                    )}
                    <span
                        className={`inline-block mt-1 text-xs px-2 py-0.5 rounded-full font-medium ${isActive ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"
                            }`}
                    >
                        {isActive ? "Active" : `Cancelled by ${room.cancelled_by_name ?? "unknown"}`}
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    <Link href="/followup" className="text-sm text-blue-600 hover:underline">
                        ← All Follow-ups
                    </Link>
                    {isActive && (
                        <button
                            onClick={handleCancel}
                            disabled={cancelling}
                            className="px-3 py-1.5 text-sm rounded-md bg-red-50 text-red-600 border border-red-200 hover:bg-red-100 disabled:opacity-50"
                        >
                            {cancelling ? "Cancelling…" : "Cancel Follow-up"}
                        </button>
                    )}
                </div>
            </div>

            {/* Pending proposal notification banner */}
            {pendingProposals.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start gap-3">
                    <span className="text-2xl">📅</span>
                    <div>
                        <p className="text-sm font-semibold text-yellow-800">
                            Your consultant proposed {pendingProposals.length === 1 ? "a time" : `${pendingProposals.length} times`} for the next session.
                        </p>
                        <button
                            onClick={() => setTab("chat")}
                            className="text-xs text-yellow-700 underline mt-1"
                        >
                            View &amp; respond in Chat →
                        </button>
                    </div>
                </div>
            )}

            {/* Tabs */}
            <div className="flex border-b border-gray-200">
                {(["health", "sessions", "chat"] as Tab[])
                    .filter((t) => isActive || t !== "health")
                    .map((t) => (
                        <button
                            key={t}
                            onClick={() => setTab(t)}
                            className={`px-5 py-2.5 text-sm font-medium capitalize transition-colors ${tab === t
                                ? "border-b-2 border-blue-600 text-blue-600"
                                : "text-gray-500 hover:text-gray-700"
                                }`}
                        >
                            {t === "health" ? "🏥 Health & Goals" : t === "sessions" ? "📋 Sessions" : "💬 Chat"}
                            {t === "chat" && pendingProposals.length > 0 && (
                                <span className="ml-1.5 bg-yellow-400 text-yellow-900 text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                                    {pendingProposals.length}
                                </span>
                            )}
                        </button>
                    ))}
            </div>

            {/* ── Health & Goals Tab ── */}
            {tab === "health" && (
                <div className="grid gap-4 sm:grid-cols-2">
                    {/* Active Goal */}
                    <div className="bg-white rounded-xl shadow p-5">
                        <h3 className="text-sm font-semibold text-gray-700 mb-3">🎯 Your Active Goal</h3>
                        {summary?.goal ? (
                            <dl className="space-y-2 text-sm">
                                <div className="flex justify-between">
                                    <dt className="text-gray-500">Type</dt>
                                    <dd className="font-medium capitalize">{summary.goal.goal_type.replace(/_/g, " ")}</dd>
                                </div>
                                <div className="flex justify-between border-t border-gray-100 pt-2 mt-2">
                                    <dt className="text-gray-500">Initial Weight</dt>
                                    <dd className="font-medium">{summary.goal.initial_weight != null ? `${summary.goal.initial_weight} kg` : "None"}</dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-gray-500">Target Weight</dt>
                                    <dd className="font-medium">{summary.goal.target_weight != null ? `${summary.goal.target_weight} kg` : "None"}</dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-gray-500">Duration</dt>
                                    <dd className="font-medium">{summary.goal.duration_days != null ? `${summary.goal.duration_days} days` : "None"}</dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-gray-500">Start Date</dt>
                                    <dd className="font-medium">
                                        {summary.goal.start_date ? new Date(summary.goal.start_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "None"}
                                    </dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-gray-500">End Date</dt>
                                    <dd className="font-medium">
                                        {summary.goal.end_date ? new Date(summary.goal.end_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "None"}
                                    </dd>
                                </div>
                            </dl>
                        ) : (
                            <div>
                                <p className="text-sm text-gray-500 mb-3">You don't have an active goal.</p>
                                <Link href="/goal" className="text-sm text-blue-600 hover:underline">
                                    Set a goal →
                                </Link>
                            </div>
                        )}
                    </div>

                    {/* Nutrition Target */}
                    <div className="bg-white rounded-xl shadow p-5">
                        <h3 className="text-sm font-semibold text-gray-700 mb-3">🥗 Nutrition Target</h3>
                        {summary?.nutrition_target ? (
                            <dl className="space-y-2 text-sm">
                                {summary.nutrition_target.calories_kcal != null && (
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Calories</dt>
                                        <dd className="font-medium">{summary.nutrition_target.calories_kcal} kcal</dd>
                                    </div>
                                )}
                                {summary.nutrition_target.protein_g != null && (
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Protein</dt>
                                        <dd className="font-medium">{summary.nutrition_target.protein_g} g</dd>
                                    </div>
                                )}
                                {summary.nutrition_target.carbs_g != null && (
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Carbs</dt>
                                        <dd className="font-medium">{summary.nutrition_target.carbs_g} g</dd>
                                    </div>
                                )}
                                {summary.nutrition_target.fat_g != null && (
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Fat</dt>
                                        <dd className="font-medium">{summary.nutrition_target.fat_g} g</dd>
                                    </div>
                                )}
                            </dl>
                        ) : (
                            <div>
                                <p className="text-sm text-gray-500 mb-3">You don't have an active nutrition target.</p>
                                <Link href="/nutrition" className="text-sm text-blue-600 hover:underline">
                                    Set a nutrition target →
                                </Link>
                            </div>
                        )}
                    </div>

                    {/* Meal Plan Setting */}
                    <div className="bg-white rounded-xl shadow p-5">
                        <h3 className="text-sm font-semibold text-gray-700 mb-3">🍽️ Meal Plan Setting</h3>
                        {summary?.meal_plan_setting ? (
                            <div className="bg-purple-50 border border-purple-100 rounded p-3">
                                <p className="text-sm font-medium text-purple-900 flex justify-between items-center mb-1">
                                    Meal Plan {summary.meal_plan_setting.active ? "(Active)" : "(Suggested)"}
                                </p>
                                {summary.meal_plan_setting.created_by_name && (
                                    <div className="flex items-center gap-1 mb-1">
                                        <span className="text-xs font-bold text-blue-600 uppercase tracking-widest">Suggested by your consultant</span>
                                    </div>
                                )}
                                {summary.meal_plan_setting.created_by_name && (
                                    <div className="text-[11px] text-purple-700 mb-2 space-y-0.5">
                                        <div>👤 <span className="font-medium">{summary.meal_plan_setting.created_by_name}</span></div>
                                        <div>✉️ <span>{summary.meal_plan_setting.created_by_email}</span></div>
                                    </div>
                                )}
                                <p className="text-xs text-purple-800 mb-2">
                                    {summary.meal_plan_setting.name} ({summary.meal_plan_setting.timed_meals_per_day} meals)
                                </p>
                                <div className="grid grid-cols-1 gap-2 text-xs text-purple-900 mt-3">
                                    {summary.meal_plan_setting.timed_meals?.map((tm, idx) => (
                                        <div key={idx} className="bg-purple-100/50 rounded p-2 border border-purple-200/50">
                                            <p className="font-semibold border-b border-purple-200/50 pb-1 mb-1">{tm.name} <span className="text-[10px] font-normal text-purple-700 capitalize">({tm.meal_time?.replace("_", " ")})</span></p>
                                            <div className="flex justify-between text-[11px]">
                                                <span>Calories: <span className="font-medium">{tm.calories_pct}%</span></span>
                                                <span>Protein: <span className="font-medium">{tm.protein_g_pct}%</span></span>
                                                <span>Carbs: <span className="font-medium">{tm.carbs_g_pct}%</span></span>
                                                <span>Fat: <span className="font-medium">{tm.fat_g_pct}%</span></span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <div>
                                <p className="text-sm text-gray-500 mb-3">You don't have a meal plan setting.</p>
                                <Link href="/meal-settings" className="text-sm text-blue-600 hover:underline">
                                    Set a meal plan →
                                </Link>
                            </div>
                        )}
                    </div>

                    {/* Goal Tracker */}
                    {summary?.goal && (
                        <div className="bg-white rounded-xl shadow p-5 sm:col-span-2">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                                <div className="flex items-center gap-2">
                                    <h3 className="text-base font-semibold text-gray-900">📈 Goal Progress</h3>
                                    {!summary.goal.active && (
                                        <span className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">Past goal</span>
                                    )}
                                </div>

                                <form onSubmit={handleLogWeight} className="flex gap-2 items-center">
                                    <input
                                        type="number"
                                        step="0.1"
                                        required
                                        value={weightInput}
                                        onChange={(e) => setWeightInput(e.target.value)}
                                        placeholder="Today's Weight (kg)"
                                        className="block w-40 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-xs px-2 py-1.5 border disabled:bg-gray-100"
                                        disabled={!isActive}
                                    />
                                    <button
                                        type="submit"
                                        disabled={loggingWeight || !weightInput || !isActive}
                                        className="inline-flex items-center px-3 py-1.5 border border-transparent shadow-sm text-xs font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
                                    >
                                        {loggingWeight ? "…" : "Log Weight"}
                                    </button>
                                </form>
                            </div>

                            <div className="border border-gray-100 rounded-lg p-2 bg-gray-50">
                                <GoalTrackerChart
                                    logs={summary.logs || []}
                                    goalType={summary.goal.goal_type}
                                    targetWeight={summary.goal.target_weight ?? null}
                                    initialWeight={summary.goal.initial_weight ?? null}
                                />
                            </div>

                            {summary.logs && summary.logs.length > 0 && (
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
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-200 bg-white">
                                                {[...summary.logs]
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
            )}

            {/* ── Sessions Tab ── */}
            {tab === "sessions" && (
                <div className="space-y-4">
                    {sessions.length === 0 ? (
                        <div className="bg-white rounded-xl shadow p-8 text-center">
                            <p className="text-gray-400 text-sm">No sessions yet in this follow-up.</p>
                        </div>
                    ) : (
                        <>
                            {/* Current sessions */}
                            {currentSessions.length > 0 && (
                                <div className="space-y-2">
                                    {reactivatedAt && (
                                        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-1">
                                            📋 Current Sessions
                                        </h3>
                                    )}
                                    {currentSessions.map((s, idx) => (
                                        <div key={s.id} className="bg-white rounded-lg shadow px-5 py-4 flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <span className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center">
                                                    {idx + 1}
                                                </span>
                                                <div>
                                                    <p className="text-sm font-medium text-gray-900">
                                                        {new Date(s.scheduled_start_at).toLocaleDateString("en-US", { weekday: "short", day: "numeric", month: "short", year: "numeric" })}
                                                        {" "}·{" "}
                                                        {new Date(s.scheduled_start_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                                    </p>
                                                    {idx === 0 && !reactivatedAt && (
                                                        <p className="text-[10px] text-blue-500 font-medium">First session</p>
                                                    )}
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${s.status === "completed" ? "bg-green-100 text-green-700" : s.status === "cancelled" ? "bg-red-100 text-red-600" : "bg-blue-100 text-blue-700"
                                                    }`}>{s.status}</span>
                                                <Link href={`/session/${s.id}`} className="text-xs text-blue-600 hover:underline font-medium">View →</Link>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Archived sessions */}
                            {archivedSessions.length > 0 && (
                                <div className="space-y-2 mt-4">
                                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-1">
                                        📁 Archived Sessions (before cancellation)
                                    </h3>
                                    {archivedSessions.map((s) => (
                                        <div key={s.id} className="bg-white rounded-lg shadow px-5 py-4 flex items-center justify-between opacity-70">
                                            <div className="flex items-center gap-3">
                                                <div>
                                                    <p className="text-sm font-medium text-gray-900">
                                                        {new Date(s.scheduled_start_at).toLocaleDateString("en-US", { weekday: "short", day: "numeric", month: "short", year: "numeric" })}
                                                        {" "}·{" "}
                                                        {new Date(s.scheduled_start_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${s.status === "completed" ? "bg-green-100 text-green-700" : s.status === "cancelled" ? "bg-red-100 text-red-600" : "bg-blue-100 text-blue-700"
                                                    }`}>{s.status}</span>
                                                <Link href={`/session/${s.id}`} className="text-xs text-blue-600 hover:underline font-medium">View →</Link>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* ── Chat Tab ── */}
            {tab === "chat" && (
                <div className="grid gap-4 lg:grid-cols-3">
                    {/* Chat */}
                    <div className="lg:col-span-2 flex flex-col bg-white rounded-xl shadow" style={{ minHeight: "60vh" }}>
                        {!isActive && (
                            <div className="px-4 py-2 bg-red-50 border-b border-red-100 text-xs text-red-700 flex items-center gap-2">
                                <span>⛔</span>
                                <span>This follow-up has been cancelled — chat history is read-only.</span>
                            </div>
                        )}
                        <div className="flex-1 overflow-y-auto p-4 space-y-3">
                            {messages.length === 0 && (
                                <p className="text-center text-gray-400 text-sm py-8">No messages yet.</p>
                            )}
                            {messages.map((m) => {
                                const mine = m.sender_user_id === me?.id;
                                if (m.is_system)
                                    return (
                                        <div key={m.id} className="flex justify-center">
                                            <span className="text-xs text-gray-500 bg-gray-100 rounded-full px-3 py-1">
                                                {m.message}
                                            </span>
                                        </div>
                                    );
                                return (
                                    <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                                        <div
                                            className={`max-w-[78%] rounded-2xl px-4 py-2 text-sm ${mine ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-900"
                                                }`}
                                        >
                                            <div className="text-[10px] opacity-60 mb-1">
                                                {new Date(m.sent_at).toLocaleString()}
                                            </div>
                                            {m.message}
                                        </div>
                                    </div>
                                );
                            })}
                            <div ref={msgEndRef} />
                        </div>
                        {isActive && (
                            <form onSubmit={handleSend} className="p-4 border-t flex gap-2">
                                <input
                                    value={newMsg}
                                    onChange={(e) => setNewMsg(e.target.value)}
                                    placeholder="Type a message…"
                                    className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                    disabled={sending}
                                />
                                <button
                                    type="submit"
                                    disabled={sending || !newMsg.trim()}
                                    className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
                                >
                                    {sending ? "…" : "Send"}
                                </button>
                            </form>
                        )}
                    </div>

                    {/* Proposals sidebar */}
                    <div className="space-y-3">
                        {pendingProposals.length > 0 ? (
                            <div className="bg-white rounded-xl shadow p-4 space-y-3">
                                <h3 className="text-sm font-semibold text-gray-900">📅 Proposed Times</h3>
                                <p className="text-xs text-gray-500">
                                    Your consultant proposed these times. Accepting will automatically create an appointment.
                                </p>
                                {pendingProposals.map((p) => (
                                    <div key={p.id} className="border border-yellow-200 bg-yellow-50 rounded-lg p-3 space-y-2">
                                        <p className="text-xs font-medium text-yellow-800">
                                            {new Date(p.start_at).toLocaleDateString("en-US", {
                                                weekday: "short",
                                                day: "numeric",
                                                month: "short",
                                            })}{" "}
                                            ·{" "}
                                            {new Date(p.start_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                            {" – "}
                                            {new Date(p.end_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                        </p>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => handleProposalAction(p.id, "accept")}
                                                className="flex-1 text-xs bg-green-600 text-white rounded py-1.5 hover:bg-green-700 font-medium"
                                            >
                                                ✓ Accept & Schedule
                                            </button>
                                            <button
                                                onClick={() => handleProposalAction(p.id, "reject")}
                                                className="flex-1 text-xs bg-red-100 text-red-700 rounded py-1.5 hover:bg-red-200"
                                            >
                                                ✕ Reject
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="bg-white rounded-xl shadow p-4 text-center">
                                <p className="text-xs text-gray-400">No pending proposals from your consultant.</p>
                            </div>
                        )}

                        {/* Proposal history */}
                        {proposals.filter((p) => p.status !== "pending").length > 0 && (
                            <div className="bg-white rounded-xl shadow p-4">
                                <h3 className="text-sm font-semibold text-gray-900 mb-2">Proposal History</h3>
                                {proposals
                                    .filter((p) => p.status !== "pending")
                                    .map((p) => (
                                        <div
                                            key={p.id}
                                            className="flex items-center justify-between text-xs py-1.5 border-b last:border-0"
                                        >
                                            <span className="text-gray-600">
                                                {new Date(p.start_at).toLocaleDateString()}
                                            </span>
                                            <span
                                                className={`px-2 py-0.5 rounded-full font-medium ${p.status === "accepted"
                                                    ? "bg-green-100 text-green-700"
                                                    : p.status === "rejected"
                                                        ? "bg-red-100 text-red-700"
                                                        : "bg-gray-100 text-gray-600"
                                                    }`}
                                            >
                                                {p.status}
                                            </span>
                                        </div>
                                    ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
