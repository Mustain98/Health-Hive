"use client";

import { useEffect, useRef, useState, FormEvent } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/components/guards/AuthGuard";
import type {
    FollowUpMessage,
    TimeProposal,
    CreateProposalRequest,
    AppointmentRead,
    FollowUpRoomRead,
    GoalLogRead,
} from "@/lib/types";
import { GoalTrackerChart } from "@/components/ui/GoalTrackerChart";
import { LogHistoryTable } from "@/components/ui/LogHistoryTable";
import { BuildPlanForm } from "@/components/consultant/BuildPlanForm";

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

type PatientSummary = {
    patient: { id: string; full_name: string | null; email: string } | null;
    user_data: {
        height_cm: number | null;
        weight_kg: number | null;
        age: number | null;
        gender: string | null;
        activity_level?: string | null;
    } | null;
    health_profile?: {
        diet_preferences: string[];
        health_conditions: string[];
        notes: string | null;
    } | null;
    bmi?: number | null;
    tdee_kcal?: number | null;
    goal: {
        goal_type: string;
        target_value: number | null;
        unit: string | null;
        active: boolean;
        start_date?: string | null;
        end_date?: string | null;
    } | null;
    nutrition_target: {
        calories_kcal: number | null;
        protein_g: number | null;
        carbs_g: number | null;
        fat_g: number | null;
        active: boolean;
    } | null;
    meal_plan_setting: {
        id: string;
        name: string;
        timed_meals_per_day: number;
        active: boolean;
        timed_meals: {
            name: string;
            meal_time: string;
            calories_pct: number;
            protein_g_pct: number;
            carbs_g_pct: number;
            fat_g_pct: number;
        }[];
        created_by_name?: string;
        created_by_email?: string;
    } | null;
    logs: GoalLogRead[];
};

type Tab = "health" | "sessions" | "chat";

export default function ConsultantFollowUpRoomPage() {
    const { roomId } = useParams<{ roomId: string }>();
    const { user: me } = useAuth();

    const [tab, setTab] = useState<Tab>("sessions");
    const [room, setRoom] = useState<FollowUpRoomRead | null>(null);
    const [summary, setSummary] = useState<PatientSummary | null>(null);
    const [sessions, setSessions] = useState<AppointmentRead[]>([]);
    const [messages, setMessages] = useState<FollowUpMessage[]>([]);
    const [proposals, setProposals] = useState<TimeProposal[]>([]);

    // Client detail data (daily goals, plans, log history) + build-plan form
    const [dailyGoals, setDailyGoals] = useState<any[]>([]);
    const [plans, setPlans] = useState<any[]>([]);
    const [logHistory, setLogHistory] = useState<any[]>([]);
    const [showBuild, setShowBuild] = useState(false);
    const [buildMsg, setBuildMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

    const [newMsg, setNewMsg] = useState("");
    const [sending, setSending] = useState(false);
    const [cancelling, setCancelling] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Proposal form
    const [showPropose, setShowPropose] = useState(false);
    const [propStart, setPropStart] = useState("");
    const [propEnd, setPropEnd] = useState("");
    const [proposing, setProposing] = useState(false);
    const [propError, setPropError] = useState<string | null>(null);

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
            const [roomData, summaryData, sessionsData, msgs, props] = await Promise.all([
                apiFetch<FollowUpRoomRead>(`/api/followup/rooms/${roomId}`),
                apiFetch<PatientSummary>(`/api/followup/rooms/${roomId}/patient-summary`),
                apiFetch<AppointmentRead[]>(`/api/followup/rooms/${roomId}/sessions`),
                apiFetch<FollowUpMessage[]>(`/api/followup/rooms/${roomId}/messages`),
                apiFetch<TimeProposal[]>(`/api/followup/rooms/${roomId}/proposals`),
            ]);
            if (roomData.reactivated_at) roomData.reactivated_at = fixDate(roomData.reactivated_at) as string;
            setRoom(roomData);
            setSummary(summaryData);
            setSessions(sessionsData.map(fixAppt));
            setMessages(msgs);
            setProposals(props.map(fixProposal));
            // Client detail data (best-effort — hidden if access is revoked)
            const clientId = roomData.user_id;
            const [dg, pl, lh] = await Promise.all([
                apiFetch<any[]>(`/api/consultant/users/${clientId}/daily-goals`).catch(() => []),
                apiFetch<any[]>(`/api/consultant/users/${clientId}/plans`).catch(() => []),
                apiFetch<any[]>(`/api/consultant/users/${clientId}/daily-goal-logs`).catch(() => []),
            ]);
            setDailyGoals(dg);
            setPlans(pl);
            setLogHistory(lh);
        } catch (e: any) {
            setError(e.message || "Failed to load follow-up room");
        } finally {
            setLoading(false);
        }
    }

    async function refreshChatData() {
        const [msgs, props] = await Promise.all([
            apiFetch<FollowUpMessage[]>(`/api/followup/rooms/${roomId}/messages`),
            apiFetch<TimeProposal[]>(`/api/followup/rooms/${roomId}/proposals`),
        ]);
        setMessages(msgs);
        setProposals(props.map(fixProposal));
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

    async function handlePropose(e: FormEvent) {
        e.preventDefault();
        if (!propStart || !propEnd) return;
        setProposing(true);
        setPropError(null);
        try {
            const payload: CreateProposalRequest = {
                start_at: new Date(propStart).toISOString(),
                end_at: new Date(propEnd).toISOString(),
            };
            await apiFetch(`/api/followup/rooms/${roomId}/proposals`, {
                method: "POST",
                body: payload,
            });
            setShowPropose(false);
            setPropStart("");
            setPropEnd("");
            await Promise.all([refreshChatData(), apiFetch<AppointmentRead[]>(`/api/followup/rooms/${roomId}/sessions`).then(s => setSessions(s.map(fixAppt)))]);
        } catch (e: any) {
            setPropError(e.message);
        } finally {
            setProposing(false);
        }
    }

    async function handleProposalAction(proposalId: string, action: "accept" | "reject" | "cancel") {
        try {
            await apiFetch(`/api/followup/proposals/${proposalId}/${action}`, { method: "POST" });
            const [msgs, props, sess] = await Promise.all([
                apiFetch<FollowUpMessage[]>(`/api/followup/rooms/${roomId}/messages`),
                apiFetch<TimeProposal[]>(`/api/followup/rooms/${roomId}/proposals`),
                apiFetch<AppointmentRead[]>(`/api/followup/rooms/${roomId}/sessions`),
            ]);
            setMessages(msgs);
            setProposals(props.map(fixProposal));
            setSessions(sess.map(fixAppt));
        } catch (e: any) {
            alert(e.message);
        }
    }

    async function handleCancel() {
        if (!confirm("Cancel this follow-up? Both you and the patient will lose access to schedule new sessions through this room.")) return;
        setCancelling(true);
        try {
            const updated = await apiFetch<FollowUpRoomRead>(`/api/followup/rooms/${roomId}/cancel`, { method: "POST" });
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

    const bmi =
        summary?.user_data?.height_cm && summary?.user_data?.weight_kg
            ? (summary.user_data.weight_kg / ((summary.user_data.height_cm / 100) ** 2)).toFixed(1)
            : null;

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
                        Follow-up — {room.other_party_name ?? "Patient"}
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
                    <Link href="/consultant/followup" className="text-sm text-blue-600 hover:underline">
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

            {/* Tabs – hide Health & Goals when room is cancelled */}
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

            {/* ── Tab: Health & Goals ── */}
            {tab === "health" && (
                <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-3">
                    {/* Vitals */}
                    <div className="bg-white rounded-xl shadow p-5">
                        <h3 className="text-sm font-semibold text-gray-700 mb-3">📊 Vitals</h3>
                        {summary?.user_data ? (
                            <dl className="space-y-2 text-sm">
                                {summary.user_data.age && (
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Age</dt>
                                        <dd className="font-medium">{summary.user_data.age} yrs</dd>
                                    </div>
                                )}
                                {summary.user_data.gender && (
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Gender</dt>
                                        <dd className="font-medium capitalize">{summary.user_data.gender}</dd>
                                    </div>
                                )}
                                {summary.user_data.height_cm && (
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Height</dt>
                                        <dd className="font-medium">{summary.user_data.height_cm} cm</dd>
                                    </div>
                                )}
                                {summary.user_data.weight_kg && (
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Weight</dt>
                                        <dd className="font-medium">{summary.user_data.weight_kg} kg</dd>
                                    </div>
                                )}
                                {summary.user_data.activity_level && (
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Activity</dt>
                                        <dd className="font-medium capitalize">{summary.user_data.activity_level.replace(/_/g, " ")}</dd>
                                    </div>
                                )}
                                {bmi && (
                                    <div className="flex justify-between border-t pt-2 mt-2">
                                        <dt className="text-gray-500">BMI</dt>
                                        <dd className="font-semibold text-blue-700">{summary.bmi ?? bmi}</dd>
                                    </div>
                                )}
                                {summary.tdee_kcal != null && (
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">TDEE</dt>
                                        <dd className="font-semibold text-blue-700">{Math.round(summary.tdee_kcal)} kcal</dd>
                                    </div>
                                )}
                            </dl>
                        ) : (
                            <p className="text-xs text-gray-400">No health data recorded.</p>
                        )}
                    </div>

                    {/* Health profile */}
                    <div className="bg-white rounded-xl shadow p-5">
                        <h3 className="text-sm font-semibold text-gray-700 mb-3">🏥 Health Profile</h3>
                        {summary?.health_profile && (summary.health_profile.health_conditions?.length || summary.health_profile.diet_preferences?.length || summary.health_profile.notes) ? (
                            <dl className="space-y-2 text-sm">
                                {summary.health_profile.health_conditions?.length > 0 && (
                                    <div>
                                        <dt className="text-gray-500">Conditions</dt>
                                        <dd className="font-medium">{summary.health_profile.health_conditions.join(", ")}</dd>
                                    </div>
                                )}
                                {summary.health_profile.diet_preferences?.length > 0 && (
                                    <div>
                                        <dt className="text-gray-500">Diet preferences</dt>
                                        <dd className="font-medium">{summary.health_profile.diet_preferences.join(", ")}</dd>
                                    </div>
                                )}
                                {summary.health_profile.notes && (
                                    <div>
                                        <dt className="text-gray-500">Notes</dt>
                                        <dd className="font-medium">{summary.health_profile.notes}</dd>
                                    </div>
                                )}
                            </dl>
                        ) : (
                            <p className="text-xs text-gray-400">No health profile on file.</p>
                        )}
                    </div>

                    {/* Goal */}
                    <div className="bg-white rounded-xl shadow p-5">
                        <h3 className="text-sm font-semibold text-gray-700 mb-3">🎯 Active Goal</h3>
                        {summary?.goal ? (
                            <dl className="space-y-2 text-sm">
                                <div className="flex justify-between">
                                    <dt className="text-gray-500">Type</dt>
                                    <dd className="font-medium capitalize">{summary.goal.goal_type.replace(/_/g, " ")}</dd>
                                </div>
                                <div className="flex justify-between border-t border-gray-100 pt-2 mt-2">
                                    <dt className="text-gray-500">Initial Weight</dt>
                                    {/* Handle target_value falling back if the API still sends it that way from existing endpoints */}
                                    <dd className="font-medium">
                                        {(summary.goal as any).initial_weight != null ? `${(summary.goal as any).initial_weight} kg` : "None"}
                                    </dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-gray-500">Target Weight</dt>
                                    <dd className="font-medium">
                                        {(summary.goal.target_value ?? (summary.goal as any).target_weight) != null ? `${summary.goal.target_value ?? (summary.goal as any).target_weight} kg` : "None"}
                                    </dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-gray-500">Duration</dt>
                                    <dd className="font-medium">
                                        {(summary.goal as any).duration_days != null ? `${(summary.goal as any).duration_days} days` : "None"}
                                    </dd>
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
                                <div className="flex justify-between">
                                    <dt className="text-gray-500">Status</dt>
                                    <dd
                                        className={`font-medium ${summary.goal.active ? "text-green-600" : "text-gray-400"
                                            }`}
                                    >
                                        {summary.goal.active ? "Active" : "Inactive"}
                                    </dd>
                                </div>
                            </dl>
                        ) : (
                            <p className="text-xs text-gray-400">No active goal set.</p>
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
                            <p className="text-xs text-gray-400">No nutrition target set.</p>
                        )}
                    </div>

                    {/* Meal Plan Setting */}
                    <div className="bg-white rounded-xl shadow p-5 relative overflow-hidden">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-sm font-semibold text-gray-700">🍽️ Meal Plan Setting</h3>
                            {summary?.meal_plan_setting && (
                                <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full uppercase ${summary.meal_plan_setting.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                                    {summary.meal_plan_setting.active ? 'Active' : 'Suggested'}
                                </span>
                            )}
                        </div>
                        {summary?.meal_plan_setting ? (
                            <div>
                                {summary.meal_plan_setting.created_by_name && (
                                    <div className="mb-3">
                                        <span className="text-xs font-bold text-blue-600 uppercase tracking-widest block mb-1">Suggested by consultant</span>
                                        <div className="text-[11px] text-blue-700 space-y-0.5">
                                            <div>👤 <span className="font-medium">{summary.meal_plan_setting.created_by_name}</span></div>
                                            <div>✉️ <span>{summary.meal_plan_setting.created_by_email}</span></div>
                                        </div>
                                    </div>
                                )}
                                <div className="flex flex-wrap gap-4 mb-4">
                                    <div>
                                        <p className="text-xs text-gray-500 font-medium">Plan Name</p>
                                        <p className="text-base font-semibold text-gray-800">{summary.meal_plan_setting.name}</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-gray-500 font-medium">Meals Per Day</p>
                                        <p className="text-base font-semibold text-gray-800">{summary.meal_plan_setting.timed_meals_per_day}</p>
                                    </div>
                                </div>
                                <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Macro Distribution</h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {summary.meal_plan_setting.timed_meals?.map((tm, idx) => (
                                        <div key={idx} className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                                            <h4 className="font-semibold text-gray-800 mb-2 capitalize text-sm">{tm.name} <span className="text-xs font-normal text-gray-500">({tm.meal_time?.replace(/_/g, " ")})</span></h4>
                                            <div className="space-y-1 text-sm">
                                                <div className="flex justify-between"><span className="text-gray-500">Calories:</span> <span className="font-medium text-gray-700">{tm.calories_pct}%</span></div>
                                                <div className="flex justify-between"><span className="text-gray-500">Protein:</span> <span className="font-medium text-gray-700">{tm.protein_g_pct}%</span></div>
                                                <div className="flex justify-between"><span className="text-gray-500">Carbs:</span> <span className="font-medium text-gray-700">{tm.carbs_g_pct}%</span></div>
                                                <div className="flex justify-between"><span className="text-gray-500">Fat:</span> <span className="font-medium text-gray-700">{tm.fat_g_pct}%</span></div>
                                            </div>
                                            {(tm as any).meal_labels && (tm as any).meal_labels.length > 0 && (
                                                <div className="mt-3 flex flex-wrap gap-1.5">
                                                    {(tm as any).meal_labels.map((lbl: string) => (
                                                        <span key={lbl} className="inline-block px-2 py-0.5 bg-blue-100 text-blue-700 text-[10px] rounded-full font-medium capitalize">{lbl.replace(/_/g, " ")}</span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <p className="text-xs text-gray-400">No meal plan setting set for this patient.</p>
                        )}
                    </div>

                    {/* Goal Tracker Chart – show if goal exists (regardless of active/cancelled) */}
                    {summary?.goal && (
                        <div className="bg-white rounded-xl shadow p-5 sm:col-span-3 mt-2">
                            <div className="flex items-center gap-2 mb-4">
                                <h3 className="text-sm font-semibold text-gray-700">📈 Goal Progress</h3>
                                {!summary.goal.active && (
                                    <span className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">Past goal</span>
                                )}
                            </div>
                            <div className="border border-gray-100 rounded-lg p-2 bg-gray-50">
                                <GoalTrackerChart
                                    logs={summary.logs || []}
                                    goalType={summary.goal.goal_type}
                                    targetWeight={(summary.goal.target_value ?? (summary.goal as any).target_weight) ?? null}
                                    initialWeight={(summary.goal as any).initial_weight ?? null}
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

                {/* ── Daily goals ── */}
                <div className="bg-white rounded-xl shadow p-5">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">✅ Daily Goals</h3>
                    {dailyGoals.length === 0 ? <p className="text-xs text-gray-400">No daily goals.</p> : (
                        <div className="space-y-2">
                            {dailyGoals.map((g: any) => (
                                <div key={g.id} className="flex items-center gap-3 p-2.5 rounded-lg border border-gray-100">
                                    <div className="flex-1">
                                        <p className="text-sm font-medium text-gray-800">{g.name}</p>
                                        <p className="text-xs text-gray-400 capitalize">
                                            {(g.goal_type || "").replace(/_/g, " ")}
                                            {g.target_value != null ? ` · ${g.target_value} ${g.unit || ""}` : ""}
                                            {" · "}
                                            {!g.days_of_week || g.days_of_week.length === 0
                                                ? "Every day"
                                                : [...g.days_of_week].sort((a: number, b: number) => a - b).map((d: number) => ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d]).join(", ")}
                                        </p>
                                    </div>
                                    <span className={`text-xs px-2 py-0.5 rounded-full ${g.active ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                                        {g.active ? "active" : "inactive"}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* ── Plans ── */}
                <div className="bg-white rounded-xl shadow p-5">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">📦 Plans</h3>
                    {plans.length === 0 ? <p className="text-xs text-gray-400">No plans yet.</p> : (
                        <div className="space-y-2">
                            {plans.map((p: any) => (
                                <div key={p.id} className="p-3 rounded-lg border border-gray-100">
                                    <p className="text-sm font-medium text-gray-800">
                                        {p.name}
                                        <span className="ml-2 text-xs px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700 capitalize">{p.source}</span>
                                        <span className={`ml-1 text-xs px-1.5 py-0.5 rounded-full ${p.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                                            {p.active ? "active" : "inactive"}
                                        </span>
                                    </p>
                                    <p className="text-xs text-gray-500 mt-1">
                                        {p.milestone ? `🎯 ${(p.milestone.milestone_type || "").replace(/_/g, " ")}${p.milestone.target_weight ? ` ${p.milestone.target_weight}kg` : ""}` : "🎯 —"}
                                        {" · "}
                                        {p.nutrition_target ? `🥗 ${p.nutrition_target.calories_kcal} kcal` : "🥗 —"}
                                        {" · "}
                                        {p.meal_setting ? `🍽 ${p.meal_setting.timed_meals_per_day}/day` : "🍽 —"}
                                        {" · "}
                                        {`✅ ${p.daily_goals?.length ?? 0} goals`}
                                    </p>
                                    {p.daily_goals?.length > 0 && (
                                        <p className="text-xs text-gray-400">{p.daily_goals.map((d: any) => d.name).join(", ")}</p>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* ── Daily log history ── */}
                <div className="bg-white rounded-xl shadow p-5">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">🗓 Daily Log History (last 30 days)</h3>
                    <LogHistoryTable history={logHistory} />
                </div>

                {/* ── Build plan ── */}
                <div className="bg-white rounded-xl shadow p-5">
                    <div className="flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-gray-700">🛠 Build Plan for Client</h3>
                        <button onClick={() => setShowBuild(!showBuild)} className="text-xs px-3 py-1.5 rounded-md bg-blue-50 text-blue-700 font-medium hover:bg-blue-100">
                            {showBuild ? "Hide" : "Open form"}
                        </button>
                    </div>
                    {buildMsg && (
                        <div className={`mt-3 px-3 py-2 rounded-md border text-sm ${buildMsg.type === "success" ? "bg-green-50 text-green-800 border-green-200" : "bg-red-50 text-red-800 border-red-200"}`}>
                            {buildMsg.text}
                        </div>
                    )}
                    {showBuild && room && (
                        <div className="mt-4">
                            <BuildPlanForm
                                userId={String(room.user_id)}
                                onCreated={async () => {
                                    setBuildMsg({ text: "Plan created — the client can now review and activate it ✅", type: "success" });
                                    setShowBuild(false);
                                    await loadAll();
                                }}
                                onError={(msg) => setBuildMsg({ text: msg, type: "error" })}
                            />
                        </div>
                    )}
                </div>
                </div>
            )}


            {/* ── Tab: Sessions ── */}
            {
                tab === "sessions" && (() => {
                    const reactivatedAt = room.reactivated_at ? new Date(room.reactivated_at) : null;
                    const archivedSessions = reactivatedAt
                        ? sessions.filter((s) => new Date(s.scheduled_start_at) < reactivatedAt)
                        : [];
                    const currentSessions = reactivatedAt
                        ? sessions.filter((s) => new Date(s.scheduled_start_at) >= reactivatedAt)
                        : sessions;

                    const SessionCard = ({ s, label }: { s: any; label?: string }) => (
                        <div className="bg-white rounded-lg shadow px-5 py-4 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div>
                                    <p className="text-sm font-medium text-gray-900">
                                        {new Date(s.scheduled_start_at).toLocaleDateString("en-US", {
                                            weekday: "short", day: "numeric", month: "short", year: "numeric",
                                        })}
                                        {" "}·{" "}
                                        {new Date(s.scheduled_start_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                    </p>
                                    {label && <p className="text-[10px] text-blue-500 font-medium">{label}</p>}
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${s.status === "completed" ? "bg-green-100 text-green-700"
                                    : s.status === "cancelled" ? "bg-red-100 text-red-600"
                                        : "bg-blue-100 text-blue-700"}`}>
                                    {s.status}
                                </span>
                                <Link href={`/consultant/session/${s.id}`} className="text-xs text-blue-600 hover:underline font-medium">
                                    Open →
                                </Link>
                            </div>
                        </div>
                    );

                    return (
                        <div className="space-y-4">
                            {sessions.length === 0 ? (
                                <div className="bg-white rounded-xl shadow p-8 text-center">
                                    <p className="text-gray-500 text-sm">No sessions yet in this follow-up.</p>
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
                                            {currentSessions.map((s) => (
                                                <SessionCard
                                                    key={s.id}
                                                    s={s}
                                                    label={s.id === room.created_from_appointment_id ? "Originating session" : undefined}
                                                />
                                            ))}
                                        </div>
                                    )}

                                    {/* Archived sessions (before reactivation) */}
                                    {archivedSessions.length > 0 && (
                                        <div className="space-y-2">
                                            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-1 mt-4">
                                                📁 Archived Sessions (before cancellation)
                                            </h3>
                                            {archivedSessions.map((s) => (
                                                <div key={s.id} className="opacity-70">
                                                    <SessionCard s={s} />
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </>
                            )}

                            {/* Schedule Next Session */}
                            {isActive && (
                                <div className="bg-white rounded-xl shadow p-5">
                                    <div className="flex items-center justify-between mb-2">
                                        <h3 className="text-sm font-semibold text-gray-900">📅 Schedule Next Session</h3>
                                        <button
                                            onClick={() => setShowPropose((v) => !v)}
                                            className="text-xs text-blue-600 hover:underline"
                                        >
                                            {showPropose ? "Cancel" : "New Proposal"}
                                        </button>
                                    </div>
                                    {showPropose ? (
                                        <form onSubmit={handlePropose} className="space-y-3 mt-3">
                                            {propError && <p className="text-xs text-red-600">{propError}</p>}
                                            <div className="grid grid-cols-2 gap-3">
                                                <div>
                                                    <label className="block text-xs text-gray-600 mb-1">Start</label>
                                                    <input
                                                        type="datetime-local"
                                                        value={propStart}
                                                        onChange={(e) => setPropStart(e.target.value)}
                                                        className="w-full text-xs border border-gray-300 rounded px-2 py-1.5 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                                        required
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-xs text-gray-600 mb-1">End</label>
                                                    <input
                                                        type="datetime-local"
                                                        value={propEnd}
                                                        onChange={(e) => setPropEnd(e.target.value)}
                                                        className="w-full text-xs border border-gray-300 rounded px-2 py-1.5 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                                        required
                                                    />
                                                </div>
                                            </div>
                                            <button
                                                type="submit"
                                                disabled={proposing}
                                                className="w-full bg-blue-600 text-white text-sm font-medium rounded-lg py-2 hover:bg-blue-700 disabled:opacity-50"
                                            >
                                                {proposing ? "Sending proposal…" : "Send Proposal to Patient 📅"}
                                            </button>
                                        </form>
                                    ) : (
                                        <p className="text-xs text-gray-400 mt-1">
                                            Propose a date and time — the patient accepts to instantly create an appointment.
                                        </p>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })()
            }

            {/* ── Tab: Chat ── */}
            {
                tab === "chat" && (
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
                                    <h3 className="text-sm font-semibold text-gray-900">📅 Pending Proposals</h3>
                                    <p className="text-xs text-gray-500">
                                        Waiting for the patient to respond.
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
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="bg-white rounded-xl shadow p-4 text-center">
                                    <p className="text-xs text-gray-400">No pending proposals set.</p>
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
                )
            }
        </div >
    );
}
