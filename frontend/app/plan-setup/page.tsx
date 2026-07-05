"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { PlanRead } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Msg = { role: string; content: string };
type SessionState = {
    id: string;
    status: "open" | "closed";
    message_count: number;
    limit_reached: boolean;
    max_messages: number;
    messages: Msg[];
};
type SessionSummary = {
    id: string;
    status: "open" | "closed";
    message_count: number;
    created_at: string;
    preview: string;
};

type StreamMeta = { message_count: number; limit_reached: boolean; status: "open" | "closed" };
type Drafts = { plans: PlanRead[] };

// Stream the assistant reply (SSE). apiFetch can't stream, so use fetch + a reader.
async function streamMessage(
    sessionId: string, content: string, referenceSessionId: string | null,
    onDelta: (d: string) => void,
): Promise<StreamMeta | null> {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/plan-setup/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ content, reference_session_id: referenceSessionId || undefined }),
    });
    if (!res.ok || !res.body) {
        let msg = `HTTP ${res.status}`;
        try { msg = (await res.json()).detail || msg; } catch { /* ignore */ }
        throw new Error(msg);
    }
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "", final: StreamMeta | null = null;
    for (; ;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const events = buf.split("\n\n");
        buf = events.pop() || "";
        for (const ev of events) {
            const line = ev.split("\n").find((l) => l.startsWith("data: "));
            if (!line) continue;
            const obj = JSON.parse(line.slice(6));
            if (obj.error) throw new Error(obj.error);
            if (obj.delta) onDelta(obj.delta);
            if (obj.done) final = obj;
        }
    }
    return final;
}

type FinalizeResult = {
    refer_to_consultant: boolean;
    reasons?: string[];
    summary?: string;
    plan_id?: string;
    milestone?: { id: string; milestone_type: string; name: string; target_weight: number | null; target_value: number | null; unit: string | null; duration_days: number | null };
    daily_goals?: { id: string; goal_type: string; name: string; target_value: number | null; unit: string | null }[];
    nutrition_target?: { id: string; calories_kcal: number; protein_g: number; carbs_g: number; fat_g: number };
    meal_setting?: { id: string; name: string; timed_meals_per_day: number; slots: { meal_time: string; name: string; calories_pct: number; description: string | null }[] };
};

export default function PlanSetupPage() {
    const [session, setSession] = useState<SessionState | null>(null);
    const [messages, setMessages] = useState<Msg[]>([]);
    const [input, setInput] = useState("");
    const [sending, setSending] = useState(false);
    const [starting, setStarting] = useState(true);
    const [finalizing, setFinalizing] = useState(false);
    const [result, setResult] = useState<FinalizeResult | null>(null);
    const [activating, setActivating] = useState(false);
    const [activated, setActivated] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [sessions, setSessions] = useState<SessionSummary[]>([]);
    const [reference, setReference] = useState<SessionSummary | null>(null);
    const [showHistory, setShowHistory] = useState(false);
    const [drafts, setDrafts] = useState<Drafts | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);

    async function loadSessions() {
        try { setSessions(await apiFetch<SessionSummary[]>("/api/plan-setup/sessions")); } catch { /* ignore */ }
    }

    async function loadDrafts() {
        try { setDrafts(await apiFetch<Drafts>("/api/plan-setup/drafts")); } catch { /* ignore */ }
    }

    // Activate / delete a whole draft PLAN.
    async function planAction(planId: string, action: "activate" | "del") {
        setError(null);
        if (action === "del" && !confirm("Delete this draft plan and its parts?")) return;
        try {
            if (action === "activate") await apiFetch(`/api/plans/${planId}/activate`, { method: "PATCH" });
            else await apiFetch(`/api/plans/${planId}`, { method: "DELETE" });
            loadDrafts();
        } catch (err: any) { setError(err.message); }
    }

    async function loadSession(id: string) {
        setResult(null); setActivated(false); setError(null);
        const s = await apiFetch<SessionState>(`/api/plan-setup/sessions/${id}`);
        setSession(s); setMessages(s.messages); setReference(null); setShowHistory(false);
    }

    async function startSession() {
        setResult(null); setActivated(false); setError(null); setReference(null);
        const s = await apiFetch<SessionState>("/api/plan-setup/sessions", { method: "POST" });
        setSession(s); setMessages(s.messages); setShowHistory(false);
        loadSessions();
    }

    // Resume the latest open session instead of always creating a new one.
    async function initSession() {
        setStarting(true); setError(null);
        try {
            const list = await apiFetch<SessionSummary[]>("/api/plan-setup/sessions");
            setSessions(list);
            const open = list.find((s) => s.status === "open");
            if (open) await loadSession(open.id);
            else await startSession();
            loadDrafts();
        } catch {
            try { await startSession(); } catch (e: any) { setError(e.message); }
        } finally {
            setStarting(false);
        }
    }

    useEffect(() => { initSession(); }, []);
    useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }, [messages]);

    async function send() {
        const content = input.trim();
        if (!content || !session || sending) return;
        setInput("");
        // optimistic: user bubble + an empty assistant bubble we stream into
        setMessages((p) => [...p, { role: "user", content }, { role: "assistant", content: "" }]);
        setSending(true);
        try {
            const meta = await streamMessage(session.id, content, reference?.id ?? null, (delta) => {
                setMessages((p) => {
                    const c = [...p];
                    c[c.length - 1] = { role: "assistant", content: c[c.length - 1].content + delta };
                    return c;
                });
            });
            if (meta) setSession((s) => (s ? { ...s, message_count: meta.message_count, limit_reached: meta.limit_reached, status: meta.status } : s));
            setReference(null);
            loadSessions();
            loadDrafts(); // agent may have created/changed drafts via tools
        } catch (err: any) {
            setError(err.message);
            setMessages((p) => p.slice(0, -1)); // drop the empty assistant bubble on error
        } finally {
            setSending(false);
        }
    }

    async function finalize() {
        if (!session) return;
        setFinalizing(true);
        setError(null);
        try {
            const r = await apiFetch<FinalizeResult>(`/api/plan-setup/sessions/${session.id}/finalize`, { method: "POST" });
            setResult(r);
            loadSessions();
            loadDrafts();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setFinalizing(false);
        }
    }

    async function activateAll() {
        if (!result || result.refer_to_consultant || !result.plan_id) return;
        setActivating(true);
        setError(null);
        try {
            await apiFetch(`/api/plans/${result.plan_id}/activate`, { method: "PATCH" });  // whole plan
            setActivated(true);
            loadDrafts();
        } catch (err: any) {
            setError(`Activation failed: ${err.message}`);
        } finally {
            setActivating(false);
        }
    }

    const limitReached = session?.limit_reached || session?.status === "closed";

    return (
        <div className="max-w-3xl mx-auto space-y-4">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">✨ AI Plan Setup</h1>
                    <p className="text-gray-500 mt-1">
                        Chat to shape your milestone, nutrition target and meal setting. When you're happy, generate the
                        drafts — they'll be saved inactive for you to review and activate.
                    </p>
                </div>
                <div className="relative flex items-center gap-2 shrink-0">
                    <button
                        onClick={() => setShowHistory((v) => !v)}
                        className="px-3 py-1.5 text-sm font-medium rounded-lg bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
                    >
                        🕘 History
                    </button>
                    <button
                        onClick={startSession}
                        className="px-3 py-1.5 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700"
                    >
                        + New chat
                    </button>
                    {showHistory && (
                        <div className="absolute right-0 top-10 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-40 max-h-96 overflow-y-auto">
                            {sessions.length === 0 ? (
                                <p className="px-4 py-6 text-sm text-gray-400 text-center">No past chats</p>
                            ) : sessions.map((s) => (
                                <div key={s.id} className={`px-3 py-2 border-b last:border-0 hover:bg-gray-50 ${session?.id === s.id ? "bg-indigo-50/40" : ""}`}>
                                    <button onClick={() => loadSession(s.id)} className="block w-full text-left">
                                        <p className="text-sm text-gray-800 line-clamp-2">{s.preview || "New chat"}</p>
                                        <p className="text-[10px] text-gray-400 mt-0.5">
                                            {new Date(s.created_at).toLocaleString()} · {s.status}
                                        </p>
                                    </button>
                                    {session?.id !== s.id && (
                                        <button
                                            onClick={() => { setReference(s); setShowHistory(false); }}
                                            className="mt-1 text-[11px] text-indigo-600 hover:underline"
                                        >
                                            Reference in current chat
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {reference && (
                <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-indigo-50 border border-indigo-200 text-sm text-indigo-800">
                    <span>💬 Referencing an earlier chat: <em>{reference.preview}</em></span>
                    <button onClick={() => setReference(null)} className="text-indigo-500 hover:text-indigo-700">✕</button>
                </div>
            )}

            {error && <div className="px-4 py-3 rounded-xl border border-red-200 bg-red-50 text-sm text-red-800">{error}</div>}

            {/* Chat */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 flex flex-col h-[60vh]">
                <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
                    {starting ? (
                        <p className="text-center text-gray-400 text-sm py-8">Starting a session…</p>
                    ) : (
                        messages.map((m, i) => (
                            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                                <div className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm whitespace-pre-wrap ${m.role === "user" ? "bg-orange-500 text-white rounded-br-sm" : "bg-gray-100 text-gray-800 rounded-bl-sm"}`}>
                                    {m.content}
                                </div>
                            </div>
                        ))
                    )}
                    {sending && <div className="flex justify-start"><div className="bg-gray-100 text-gray-400 px-4 py-2 rounded-2xl text-sm">typing…</div></div>}
                </div>

                {/* Composer */}
                <div className="border-t border-gray-100 p-3">
                    {limitReached ? (
                        <div className="flex items-center justify-between gap-3">
                            <p className="text-sm text-amber-700">Chat limit reached for this session.</p>
                            <button onClick={startSession} className="px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700">
                                Start a new session
                            </button>
                        </div>
                    ) : (
                        <div className="flex gap-2">
                            <input
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                                placeholder="Describe your goal, timeframe, preferences…"
                                disabled={sending || starting}
                                className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-orange-500 focus:ring-orange-500"
                            />
                            <button onClick={send} disabled={sending || !input.trim()} className="px-4 py-2 text-sm font-semibold rounded-lg bg-orange-500 text-white hover:bg-orange-600 disabled:opacity-50">
                                Send
                            </button>
                        </div>
                    )}
                    <div className="flex items-center justify-between mt-2">
                        <span className="text-xs text-gray-400">{session ? `${session.message_count}/${session.max_messages} messages` : ""}</span>
                        <button onClick={finalize} disabled={finalizing || starting || messages.length < 2} className="px-4 py-1.5 text-sm font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50">
                            {finalizing ? "Generating…" : "✅ Finalize & generate drafts"}
                        </button>
                    </div>
                </div>
            </div>

            {/* Pending draft plans — review & activate as a unit */}
            {drafts && drafts.plans.length > 0 && (
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4">
                    <div>
                        <h2 className="text-lg font-semibold text-gray-900">Draft plans</h2>
                        <p className="text-xs text-gray-500">Nothing is live until you activate a plan. Manage all plans on the Plans page.</p>
                    </div>
                    {drafts.plans.map((p) => (
                        <div key={p.id} className="rounded-xl border border-gray-200 p-4 space-y-2">
                            <div className="flex items-center justify-between gap-2">
                                <p className="font-semibold text-gray-900">{p.name}</p>
                                <div className="flex gap-2">
                                    <button onClick={() => planAction(p.id, "activate")} className="text-xs px-3 py-1 rounded-lg font-medium bg-emerald-600 text-white hover:bg-emerald-700">Activate plan</button>
                                    <button onClick={() => planAction(p.id, "del")} className="text-xs px-2 py-1 rounded-lg font-medium bg-white border border-red-200 text-red-600 hover:bg-red-50">✕</button>
                                </div>
                            </div>
                            <ul className="text-sm text-gray-600 space-y-0.5">
                                <li>🎯 {p.milestone ? `${(p.milestone.milestone_type || "").replace(/_/g, " ")}${p.milestone.name ? ` — ${p.milestone.name}` : ""}${p.milestone.duration_days ? ` (${p.milestone.duration_days}d)` : ""}` : <span className="text-gray-300">no milestone</span>}</li>
                                <li>🍽️ {p.nutrition_target ? `${p.nutrition_target.calories_kcal} kcal · P${Math.round(p.nutrition_target.protein_g)} C${Math.round(p.nutrition_target.carbs_g)} F${Math.round(p.nutrition_target.fat_g)}` : <span className="text-gray-300">no nutrition target</span>}</li>
                                <li>📋 {p.meal_setting ? `${p.meal_setting.name} · ${p.meal_setting.timed_meals_per_day} meals` : <span className="text-gray-300">no meal setting</span>}</li>
                                <li>✅ {p.daily_goals.length ? p.daily_goals.map((d) => d.name).join(", ") : <span className="text-gray-300">no daily goals</span>}</li>
                            </ul>
                            {p.missing.length > 0 && <p className="text-[11px] text-amber-600">Missing: {p.missing.map((m) => m.replace(/_/g, " ")).join(", ")}</p>}
                        </div>
                    ))}
                </div>
            )}

            {/* Finalize overlay */}
            {result && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" onClick={() => setResult(null)}>
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[88vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                        <div className="px-6 py-4 border-b flex items-center justify-between sticky top-0 bg-white">
                            <h2 className="text-lg font-bold text-gray-900">{result.refer_to_consultant ? "Needs a consultant" : "Review your plan drafts"}</h2>
                            <button onClick={() => setResult(null)} className="text-gray-400 hover:text-gray-700">✕</button>
                        </div>

                        <div className="p-6 space-y-4">
                            {result.refer_to_consultant ? (
                                <div className="space-y-3">
                                    <p className="text-sm text-gray-700">This goal looks aggressive, so we didn't auto-generate it. A consultant can set it up safely.</p>
                                    {result.reasons?.length ? (
                                        <ul className="list-disc list-inside text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
                                            {result.reasons.map((r, i) => <li key={i}>{r}</li>)}
                                        </ul>
                                    ) : null}
                                    <a href="/consultants" className="inline-block px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700">Find a consultant</a>
                                </div>
                            ) : activated ? (
                                <div className="text-center py-6 space-y-3">
                                    <div className="text-4xl">🎉</div>
                                    <p className="text-gray-800 font-semibold">Everything activated!</p>
                                    <a href="/meal-plan" className="inline-block px-4 py-2 text-sm font-semibold rounded-lg bg-orange-500 text-white hover:bg-orange-600">Generate a meal plan</a>
                                </div>
                            ) : (
                                <>
                                    {result.summary && <p className="text-sm text-gray-600 italic">{result.summary}</p>}

                                    {result.milestone && (
                                        <div className="rounded-xl border border-gray-200 p-4">
                                            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Milestone</p>
                                            <p className="font-semibold text-gray-900">{result.milestone.name}</p>
                                            <p className="text-sm text-gray-500 capitalize">
                                                {result.milestone.milestone_type.replace(/_/g, " ")}
                                                {result.milestone.target_weight ? ` · target ${result.milestone.target_weight} kg` : ""}
                                                {result.milestone.target_value ? ` · ${result.milestone.target_value} ${result.milestone.unit || ""}` : ""}
                                                {result.milestone.duration_days ? ` · ${result.milestone.duration_days} days` : ""}
                                            </p>
                                        </div>
                                    )}

                                    {result.daily_goals && result.daily_goals.length > 0 && (
                                        <div className="rounded-xl border border-gray-200 p-4">
                                            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Daily Goals</p>
                                            <ul className="space-y-1">
                                                {result.daily_goals.map((d) => (
                                                    <li key={d.id} className="text-sm text-gray-700">• {d.name}{d.target_value ? ` — ${d.target_value} ${d.unit || ""}` : ""}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {result.nutrition_target && (
                                        <div className="rounded-xl border border-gray-200 p-4">
                                            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Nutrition Target</p>
                                            <p className="text-sm text-gray-700">
                                                {result.nutrition_target.calories_kcal} kcal · P {result.nutrition_target.protein_g}g · C {result.nutrition_target.carbs_g}g · F {result.nutrition_target.fat_g}g
                                            </p>
                                        </div>
                                    )}

                                    {result.meal_setting && (
                                        <div className="rounded-xl border border-gray-200 p-4">
                                            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Meal Setting · {result.meal_setting.name}</p>
                                            <ul className="space-y-1">
                                                {result.meal_setting.slots.map((s, i) => (
                                                    <li key={i} className="text-sm text-gray-700">
                                                        <span className="capitalize font-medium">{s.meal_time}</span> · {Math.round(s.calories_pct)}%
                                                        {s.description ? <span className="text-gray-400"> — {s.description}</span> : null}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    <div className="flex gap-2 pt-2">
                                        <button onClick={activateAll} disabled={activating} className="px-5 py-2.5 text-sm font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50">
                                            {activating ? "Activating…" : "Activate all"}
                                        </button>
                                        <button onClick={() => setResult(null)} className="px-5 py-2.5 text-sm font-semibold rounded-lg bg-white text-gray-600 border border-gray-300 hover:bg-gray-50">
                                            Keep chatting
                                        </button>
                                    </div>
                                    <p className="text-xs text-gray-400">Drafts are saved inactive — you can also review/activate them later from Goal, Nutrition and Meal Settings.</p>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
