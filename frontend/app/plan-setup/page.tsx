"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { PlanRead } from "@/lib/types";
import { TOOL_LABELS, formatGoalDetail, formatDays, milestoneTypeLabel } from "@/lib/format";
import { PlanSummary } from "@/components/plan/PlanSummary";
import { DraftPlanPicker, NEW_PLAN, type DraftChoice } from "@/components/plan/DraftPlanPicker";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Msg = { role: string; content: string };
type SessionState = {
    id: string;
    status: "open" | "closed";
    message_count: number;
    limit_reached: boolean;
    max_messages: number;
    approval_mode: boolean;
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

/** One proposed write awaiting the user's decision. */
type PendingItem = {
    tool: string;
    args: Record<string, unknown>;
    description?: string;
    /** Deletes cannot be edited into something else — the backend omits "edit". */
    allowed: ("approve" | "edit" | "reject")[];
};

/** The full batch the assistant proposed — reviewed item by item. */
type PendingApproval = { requests: PendingItem[] };

/** The user's choice for one item. Edit requires a note; reject's is optional. */
type ItemDecision = { decision: "approve" | "edit" | "reject"; note: string };

/**
 * The backend flattens LangChain's interrupt into a stable shape:
 *   { requests: [{ interrupt_id, tool, args, description, allowed }] }
 * so this stays decoupled from middleware internals. ALL items are kept — a batch
 * of 10 daily goals is 10 reviewable rows, not just the first.
 */
function parseInterrupt(raw: unknown): PendingApproval | null {
    const reqs = (raw as { requests?: Record<string, unknown>[] } | null)?.requests;
    if (!reqs || reqs.length === 0) return null;
    const items: PendingItem[] = reqs.map((req) => {
        const allowed: PendingItem["allowed"] = [];
        for (const d of (req.allowed ?? ["approve", "reject"]) as string[]) {
            if (d === "approve" || d === "edit" || d === "reject") allowed.push(d);
        }
        return {
            tool: String(req.tool ?? "this change"),
            args: (req.args && typeof req.args === "object" ? req.args : {}) as Record<string, unknown>,
            description: req.description as string | undefined,
            allowed: allowed.length ? allowed : ["approve", "reject"],
        };
    });
    return { requests: items };
}

/** Plain-language summary of one proposed item — the user never reads raw fields. */
function describeItem(req: PendingItem): React.ReactNode {
    const a = req.args as Record<string, any>;
    let detail: React.ReactNode = "";

    if (req.tool.includes("daily_goal")) {
        const d = formatGoalDetail({
            target_value: a.target_value, unit: a.unit,
            attributes: a.attributes, days_of_week: a.days_of_week,
        });
        detail = [d, formatDays(a.days_of_week)].filter(Boolean).join(" · ");
    } else if (req.tool.includes("milestone")) {
        const bits = [milestoneTypeLabel(a.milestone_type)];
        if (a.target_weight != null) bits.push(`target ${a.target_weight} ${a.unit || "kg"}`);
        if (a.target_value != null) bits.push(`${a.target_value} ${a.unit || ""}`.trim());
        if (a.duration_days != null) bits.push(`${a.duration_days} days`);
        const attrs = a.attributes || {};
        if (attrs.target_muscle_kg != null) bits.push(`+${attrs.target_muscle_kg} kg muscle`);
        if (attrs.target_fat_loss_kg != null) bits.push(`−${attrs.target_fat_loss_kg} kg fat`);
        detail = bits.filter(Boolean).join(" · ");
    } else if (req.tool.includes("nutrition_target")) {
        const bits = [];
        if (a.calories_kcal != null) bits.push(`${a.calories_kcal} kcal`);
        if (a.protein_g != null) bits.push(`P${Math.round(a.protein_g)}`);
        if (a.carbs_g != null) bits.push(`C${Math.round(a.carbs_g)}`);
        if (a.fat_g != null) bits.push(`F${Math.round(a.fat_g)}`);
        detail = bits.join(" · ") || "derived from your milestone";
    } else if (req.tool.includes("meal_setting")) {
        const slots = Array.isArray(a.slots) ? a.slots : [];
        if (slots.length) {
            detail = (
                <ul className="list-disc pl-4 space-y-1">
                    {slots.map((s: any, idx) => (
                        <li key={idx}>
                            <span className="font-medium">{s.name || s.meal_time}</span>
                            <span className="text-gray-500 ml-1">{s.calories_pct ?? "?"}%</span>
                            {(s.protein_g_pct !== undefined || s.carbs_g_pct !== undefined || s.fat_g_pct !== undefined) && (
                                <span className="text-gray-400 text-xs ml-1">
                                    (P{s.protein_g_pct ?? s.calories_pct}% C{s.carbs_g_pct ?? s.calories_pct}% F{s.fat_g_pct ?? s.calories_pct}%)
                                </span>
                            )}
                            {s.meal_labels && s.meal_labels.length > 0 && (
                                <span className="text-indigo-400 text-xs ml-2 font-medium">[{s.meal_labels.join(", ")}]</span>
                            )}
                            {s.description && <span className="text-gray-400 ml-2">— {s.description}</span>}
                        </li>
                    ))}
                </ul>
            );
        } else {
            detail = "meal split";
        }
    } else {
        detail = req.description || "";
    }

    return (
        <div className="space-y-1">
            <div>{detail}</div>
            {a.reasoning && (
                <div className="text-emerald-700 italic border-l-2 border-emerald-200 pl-2 mt-2">
                    💡 {a.reasoning}
                </div>
            )}
        </div>
    );
}

/** The backend's `choice` frame: the draft plans this chat may be pointed at.
 * Shaped like parseInterrupt — tolerate anything, render only what we understand. */
function parseChoice(raw: unknown): DraftChoice | null {
    const o = raw as Record<string, any> | null;
    if (!o || o.kind !== "choose_draft_plan") return null;
    const plans: PlanRead[] = Array.isArray(o.plans) ? o.plans : [];
    const allowNew = o.allow_new !== false;
    if (!plans.length && !allowNew) return null;  // nothing to click
    return {
        kind: "choose_draft_plan",
        reason: o.reason === "empty_draft_exists" ? "empty_draft_exists" : "unpinned_with_drafts",
        plans,
        allowNew,
        resume: Array.isArray(o.resume?.decisions) ? { decisions: o.resume.decisions } : null,
    };
}

type StreamResult = {
    meta: StreamMeta | null;
    interrupt: PendingApproval | null;
    choice: DraftChoice | null;
};

/** Read one SSE stream: text deltas, an optional pending approval, and the final meta.
 * A `reset` frame means "what streamed so far was pre-tool narration, not the answer" —
 * the current assistant bubble is cleared and streaming starts over. */
async function readStream(res: Response, onDelta: (d: string) => void,
    onReset?: () => void): Promise<StreamResult> {
    if (!res.ok || !res.body) {
        let msg = `HTTP ${res.status}`;
        try { msg = (await res.json()).detail || msg; } catch { /* ignore */ }
        throw new Error(msg);
    }
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "", meta: StreamMeta | null = null, interrupt: PendingApproval | null = null;
    let choice: DraftChoice | null = null;
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
            if (obj.reset && onReset) onReset();
            if (obj.delta) onDelta(obj.delta);
            if (obj.interrupt) interrupt = parseInterrupt(obj.interrupt);
            if (obj.choice) choice = parseChoice(obj.choice);
            if (obj.done) meta = obj;
        }
    }
    return { meta, interrupt, choice };
}

// Stream the assistant reply (SSE). apiFetch can't stream, so use fetch + a reader.
async function streamMessage(
    sessionId: string, content: string, referenceSessionId: string | null,
    onDelta: (d: string) => void, onReset?: () => void,
): Promise<StreamResult> {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/plan-setup/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ content, reference_session_id: referenceSessionId || undefined }),
    });
    return readStream(res, onDelta, onReset);
}

/** Send the per-item decisions and let the run continue. */
async function streamResume(
    sessionId: string,
    decisions: { decision: "approve" | "edit" | "reject"; message?: string }[],
    onDelta: (d: string) => void, onReset?: () => void,
): Promise<StreamResult> {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/plan-setup/sessions/${sessionId}/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ decisions }),
    });
    return readStream(res, onDelta, onReset);
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
    // The batch of proposed writes awaiting review, and the user's per-item choices.
    const [pending, setPending] = useState<PendingApproval | null>(null);
    const [decisions, setDecisions] = useState<ItemDecision[]>([]);
    // The draft-plan slots to pick from, when a write is blocked on "which plan?".
    const [choice, setChoice] = useState<DraftChoice | null>(null);
    const [choiceBusy, setChoiceBusy] = useState<string | null>(null);
    const [choiceError, setChoiceError] = useState<string | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);

    async function loadSessions() {
        try { setSessions(await apiFetch<SessionSummary[]>("/api/plan-setup/sessions")); } catch { /* ignore */ }
    }

    async function loadDrafts() {
        try { setDrafts(await apiFetch<Drafts>("/api/plan-setup/drafts")); } catch (err: any) { setError(err.message); }
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
    useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }, [messages, pending, choice]);

    /** Append streamed text to the assistant bubble we're currently filling. */
    const appendDelta = (delta: string) =>
        setMessages((p) => {
            const c = [...p];
            c[c.length - 1] = { role: "assistant", content: c[c.length - 1].content + delta };
            return c;
        });

    /** A reset frame: what streamed so far was pre-tool narration — clear the bubble. */
    const resetBubble = () =>
        setMessages((p) => {
            const c = [...p];
            c[c.length - 1] = { role: "assistant", content: "" };
            return c;
        });

    function applyResult(r: StreamResult) {
        if (r.meta) {
            const m = r.meta;
            setSession((s) => (s ? { ...s, message_count: m.message_count, limit_reached: m.limit_reached, status: m.status } : s));
        }
        setPending(r.interrupt);
        // Every item defaults to Save, so "accept all" is a single click.
        setDecisions(r.interrupt
            ? r.interrupt.requests.map(() => ({ decision: "approve" as const, note: "" }))
            : []);
        setChoice(r.choice);
        setChoiceError(null);
        loadSessions();
        loadDrafts(); // agent may have created/changed drafts via tools
    }

    async function send() {
        const content = input.trim();
        if (!content || !session || sending) return;
        setInput("");
        setChoice(null);  // answering in words instead of clicking dismisses the picker
        // optimistic: user bubble + an empty assistant bubble we stream into
        setMessages((p) => [...p, { role: "user", content }, { role: "assistant", content: "" }]);
        setSending(true);
        try {
            applyResult(await streamMessage(session.id, content, reference?.id ?? null, appendDelta, resetBubble));
            setReference(null);
        } catch (err: any) {
            setError(err.message);
            setMessages((p) => p.slice(0, -1)); // drop the empty assistant bubble on error
        } finally {
            setSending(false);
        }
    }

    /** The user picked a draft slot (or "create new"): point the chat at it, then let the
     * agent finish the write it was blocked on. `planId === null` means create new. */
    async function chooseDraft(planId: string | null) {
        if (!session || !choice || choiceBusy || sending) return;
        setChoiceBusy(planId ?? NEW_PLAN);
        setChoiceError(null);
        try {
            // Pin FIRST, before touching the transcript. If this fails the chat must show
            // no trace of a decision that never happened — and on the resume branch,
            // consuming the approval here would lose the user's approved writes.
            if (planId) {
                await apiFetch(`/api/plan-setup/sessions/${session.id}/draft-plan`,
                    { method: "PATCH", body: { plan_id: planId } });
            } else {
                await apiFetch(`/api/plan-setup/sessions/${session.id}/new-draft-plan`,
                    { method: "POST" });
            }
        } catch (err) {
            // The slot list was drawn a moment ago; the plan may have been activated (409)
            // or deleted (404) since. Refresh it in place and leave the picker up.
            const e = err as ApiError;
            setChoiceError(
                e.status === 409 ? "That plan went live since this list was drawn — pick another."
                    : e.status === 404 ? "That plan no longer exists — pick another."
                        : e.message);
            try {
                const fresh = await apiFetch<Drafts>("/api/plan-setup/drafts");
                setDrafts(fresh);
                setChoice((c) => (c ? { ...c, plans: fresh.plans } : c));
            } catch { /* keep the stale list rather than blanking the picker */ }
            return;
        } finally {
            setChoiceBusy(null);
        }

        // Pinned. Carry on with whatever the agent was blocked on.
        const c = choice;
        setChoice(null);
        // Deliberately keyword-free: this text is what route_turn() sees, and anything like
        // "goal"/"meal"/"calories" would route the turn to a narrower specialist than the
        // blocked write needs. With no keyword it falls through to the coach, which holds
        // every tool. Past tense, so the model doesn't re-run start_new_draft_plan.
        const bubble = planId
            ? "Use the draft plan I just picked — go ahead with what I asked for."
            : "I've started a brand-new draft plan — go ahead with what I asked for.";
        setMessages((p) => [...p, { role: "user", content: bubble }, { role: "assistant", content: "" }]);
        setSending(true);
        try {
            applyResult(c.resume
                ? await streamResume(session.id, c.resume.decisions, appendDelta, resetBubble)
                : await streamMessage(session.id, bubble, null, appendDelta, resetBubble));
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
            setMessages((p) => p.slice(0, -1));
        } finally {
            setSending(false);
        }
    }

    /** Flip "Ask before saving" for this chat. Optimistic; server state wins on error. */
    async function toggleApproval() {
        if (!session || sending) return;
        const next = !session.approval_mode;
        setSession((s) => (s ? { ...s, approval_mode: next } : s));
        try {
            const updated = await apiFetch<SessionState>(`/api/plan-setup/sessions/${session.id}`, {
                method: "PATCH",
                body: { approval_mode: next },  // apiFetch stringifies
            });
            setSession(updated);
        } catch (err) {
            setSession((s) => (s ? { ...s, approval_mode: !next } : s)); // revert
            setError(err instanceof Error ? err.message : String(err));
        }
    }

    /** Update one item's choice or note. */
    function setItemDecision(i: number, patch: Partial<ItemDecision>) {
        setDecisions((d) => d.map((x, idx) => (idx === i ? { ...x, ...patch } : x)));
    }

    /** Send all per-item decisions in one call. Approved items save exactly once;
     * edited/rejected ones come back corrected as a follow-up approval. */
    async function sendDecisions() {
        if (!session || !pending || sending) return;
        // Edit without a note is meaningless — the note IS the edit.
        const missing = decisions.findIndex((d) => d.decision === "edit" && !d.note.trim());
        if (missing !== -1) {
            setError(`Item ${missing + 1}: say what should change before sending.`);
            return;
        }
        setError(null);
        const payload = decisions.map((d) => ({
            decision: d.decision,
            ...(d.note.trim() ? { message: d.note.trim() } : {}),
        }));
        // A compact transcript bubble so the chat reads as a conversation.
        const summary = decisions
            .map((d, i) => {
                const name = (pending.requests[i]?.args?.name as string) || TOOL_LABELS[pending.requests[i]?.tool] || `item ${i + 1}`;
                const icon = d.decision === "approve" ? "✅" : d.decision === "edit" ? "✏️" : "✕";
                return `${icon} ${name}${d.note.trim() ? ` — ${d.note.trim()}` : ""}`;
            })
            .join("  ·  ");
        setPending(null);
        setDecisions([]);
        setMessages((p) => [...p, { role: "user", content: summary }, { role: "assistant", content: "" }]);
        setSending(true);
        try {
            applyResult(await streamResume(session.id, payload, appendDelta, resetBubble));
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
            setMessages((p) => p.slice(0, -1));
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
                    {session && (
                        <label className="flex items-center gap-2 mr-1 cursor-pointer select-none"
                            title="When on, the assistant asks you to approve, edit or reject every change before it is saved.">
                            <span className="text-xs font-medium text-gray-600">Ask before saving</span>
                            <button
                                role="switch"
                                aria-checked={session.approval_mode}
                                disabled={sending || !!pending}
                                onClick={toggleApproval}
                                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors disabled:opacity-50 ${session.approval_mode ? "bg-emerald-500" : "bg-gray-300"}`}
                            >
                                <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${session.approval_mode ? "translate-x-4.5" : "translate-x-0.5"}`} />
                            </button>
                        </label>
                    )}
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

                    {/* Pending approval — the assistant wants to write something */}
                    {pending && !sending && (
                        <div className="rounded-2xl border-2 border-amber-300 bg-amber-50 p-4 space-y-3">
                            <div>
                                <p className="text-sm font-semibold text-amber-900">
                                    Review before saving — {pending.requests.length} proposed {pending.requests.length === 1 ? "change" : "changes"}
                                </p>
                                <p className="text-xs text-amber-800 mt-0.5">
                                    Save what looks right, describe changes for what doesn&apos;t, reject what you don&apos;t want at all.
                                </p>
                            </div>

                            <div className="space-y-2">
                                {pending.requests.map((req, i) => {
                                    const d = decisions[i] ?? { decision: "approve", note: "" };
                                    const canEdit = req.allowed.includes("edit");
                                    return (
                                        <div key={i} className="rounded-lg bg-white border border-amber-200 p-3 space-y-2">
                                            <div className="flex items-start justify-between gap-3">
                                                <div className="min-w-0">
                                                    <p className="text-sm font-semibold text-gray-900">
                                                        {TOOL_LABELS[req.tool] || req.tool.replace(/_/g, " ")}
                                                        {typeof req.args.name === "string" && <> — {req.args.name}</>}
                                                    </p>
                                                    <p className="text-xs text-gray-600 mt-0.5">{describeItem(req)}</p>
                                                </div>
                                                {/* Save / Edit / Reject segmented control */}
                                                <div className="flex rounded-lg border border-gray-200 overflow-hidden shrink-0 text-xs font-semibold">
                                                    <button onClick={() => setItemDecision(i, { decision: "approve" })}
                                                        className={`px-2.5 py-1.5 ${d.decision === "approve" ? "bg-emerald-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}>
                                                        ✅ Save
                                                    </button>
                                                    {canEdit && (
                                                        <button onClick={() => setItemDecision(i, { decision: "edit" })}
                                                            className={`px-2.5 py-1.5 border-l border-gray-200 ${d.decision === "edit" ? "bg-amber-500 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}>
                                                            ✏️ Edit
                                                        </button>
                                                    )}
                                                    <button onClick={() => setItemDecision(i, { decision: "reject" })}
                                                        className={`px-2.5 py-1.5 border-l border-gray-200 ${d.decision === "reject" ? "bg-red-500 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}>
                                                        ✕ Reject
                                                    </button>
                                                </div>
                                            </div>
                                            {d.decision === "edit" && (
                                                <input
                                                    value={d.note}
                                                    onChange={(e) => setItemDecision(i, { note: e.target.value })}
                                                    placeholder="What should change? e.g. make it 4 sets, move to Tuesday…"
                                                    className="w-full rounded-lg border border-amber-300 px-3 py-1.5 text-sm focus:border-amber-500 focus:ring-amber-500"
                                                    autoFocus
                                                />
                                            )}
                                            {d.decision === "reject" && (
                                                <input
                                                    value={d.note}
                                                    onChange={(e) => setItemDecision(i, { note: e.target.value })}
                                                    placeholder="Why? (optional — helps it propose something better instead)"
                                                    className="w-full rounded-lg border border-red-200 px-3 py-1.5 text-sm focus:border-red-400 focus:ring-red-400"
                                                />
                                            )}
                                        </div>
                                    );
                                })}
                            </div>

                            <div className="flex items-center justify-between gap-3">
                                <p className="text-[11px] text-amber-700">
                                    Saved items are final. Edited and rejected ones come back as a new proposal — nothing is lost.
                                </p>
                                <button onClick={sendDecisions}
                                    className="px-4 py-1.5 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 shrink-0">
                                    Send decisions
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Which draft plan? — clickable slots instead of a prose question */}
                    {choice && !sending && (
                        <DraftPlanPicker choice={choice} busy={choiceBusy} error={choiceError}
                            onPick={chooseDraft} />
                    )}
                </div>

                {/* Composer */}
                <div className="border-t border-gray-100 p-3">
                    {pending && !sending ? (
                        <p className="text-sm text-amber-700 px-1">
                            Respond to the pending change above to continue.
                        </p>
                    ) : limitReached ? (
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
            {drafts && (
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4">
                    <div>
                        <h2 className="text-lg font-semibold text-gray-900">Draft plans</h2>
                        <p className="text-xs text-gray-500">Nothing is live until you activate a plan. Manage all plans on the Plans page.</p>
                    </div>
                    {drafts.plans.length === 0 ? (
                        <div className="text-center py-6 border-2 border-dashed border-gray-200 rounded-xl">
                            <p className="text-sm text-gray-500">No draft plans yet.</p>
                        </div>
                    ) : (
                        drafts.plans.map((p) => (
                            <div key={p.id} className="rounded-xl border border-gray-200 p-4 space-y-3">
                                <div className="flex items-center justify-between gap-2 border-b border-gray-100 pb-2">
                                    <p className="font-bold text-gray-900">{p.name}</p>
                                    <div className="flex gap-2">
                                        <button onClick={() => planAction(p.id, "activate")} className="text-xs px-3 py-1 rounded-lg font-medium bg-emerald-600 text-white hover:bg-emerald-700">Activate plan</button>
                                        <button onClick={() => planAction(p.id, "del")} className="text-xs px-2 py-1 rounded-lg font-medium bg-white border border-red-200 text-red-600 hover:bg-red-50">✕</button>
                                    </div>
                                </div>
                                <PlanSummary plan={p} />
                            </div>
                        ))
                    )}
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
                                            <ul className="space-y-2">
                                                {result.meal_setting.slots.map((s, i) => (
                                                    <li key={i} className="text-sm text-gray-700">
                                                        <div>
                                                            <span className="capitalize font-medium">{s.meal_time}</span> · {Math.round(s.calories_pct)}%
                                                            {s.description && <span className="text-gray-500 ml-1">— {s.description}</span>}
                                                        </div>
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
