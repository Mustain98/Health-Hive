"use client";

import { useEffect, useRef, useState, FormEvent } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/components/guards/AuthGuard";
import type {
    ConsultationChatRead,
    ConsultationMessageRead,
    ConsultationProposalRead,
} from "@/lib/types";

const WS_BASE =
    process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, "ws") || "ws://127.0.0.1:8000";

export function ConsultationChat({ chatId, backHref }: { chatId: string; backHref: string }) {
    const { user: me } = useAuth();

    const [chat, setChat] = useState<ConsultationChatRead | null>(null);
    const [messages, setMessages] = useState<ConsultationMessageRead[]>([]);
    const [proposals, setProposals] = useState<ConsultationProposalRead[]>([]);

    const [newMsg, setNewMsg] = useState("");
    const [sending, setSending] = useState(false);

    const [proposeStart, setProposeStart] = useState("");
    const [proposeEnd, setProposeEnd] = useState("");
    const [proposing, setProposing] = useState(false);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const msgEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        loadAll();
    }, [chatId]);

    useEffect(() => {
        if (!chatId) return;
        const ws = new WebSocket(`${WS_BASE}/api/consultations/ws/${chatId}`);
        wsRef.current = ws;
        ws.onmessage = (e) => {
            try {
                const incoming = JSON.parse(e.data) as ConsultationMessageRead;
                setMessages((prev) =>
                    prev.some((m) => m.id === incoming.id) ? prev : [...prev, incoming]
                );
            } catch { /* ignore */ }
        };
        return () => ws.close();
    }, [chatId]);

    useEffect(() => {
        msgEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    async function loadAll() {
        setLoading(true);
        try {
            const [chatData, msgs, props] = await Promise.all([
                apiFetch<ConsultationChatRead>(`/api/consultations/chats/${chatId}`),
                apiFetch<ConsultationMessageRead[]>(`/api/consultations/chats/${chatId}/messages`),
                apiFetch<ConsultationProposalRead[]>(`/api/consultations/chats/${chatId}/proposals`),
            ]);
            setChat(chatData);
            setMessages(msgs);
            setProposals(props);
        } catch (e: any) {
            setError(e.message || "Failed to load chat");
        } finally {
            setLoading(false);
        }
    }

    async function refresh() {
        const [msgs, props] = await Promise.all([
            apiFetch<ConsultationMessageRead[]>(`/api/consultations/chats/${chatId}/messages`),
            apiFetch<ConsultationProposalRead[]>(`/api/consultations/chats/${chatId}/proposals`),
        ]);
        setMessages(msgs);
        setProposals(props);
    }

    async function handleSend(e: FormEvent) {
        e.preventDefault();
        if (!newMsg.trim() || sending) return;
        setSending(true);
        try {
            const saved = await apiFetch<ConsultationMessageRead>(
                `/api/consultations/chats/${chatId}/messages`,
                { method: "POST", body: { message: newMsg } }
            );
            setMessages((prev) => (prev.some((m) => m.id === saved.id) ? prev : [...prev, saved]));
            wsRef.current?.send(JSON.stringify(saved));
            setNewMsg("");
        } catch (e: any) {
            alert(e.message);
        } finally {
            setSending(false);
        }
    }

    async function handlePropose(e: FormEvent) {
        e.preventDefault();
        if (!proposeStart || !proposeEnd || proposing) return;
        setProposing(true);
        try {
            await apiFetch(`/api/consultations/chats/${chatId}/proposals`, {
                method: "POST",
                body: {
                    start_at: new Date(proposeStart).toISOString(),
                    end_at: new Date(proposeEnd).toISOString(),
                },
            });
            setProposeStart("");
            setProposeEnd("");
            await refresh();
        } catch (e: any) {
            alert(e.message);
        } finally {
            setProposing(false);
        }
    }

    async function handleProposalAction(id: string, action: "accept" | "reject" | "cancel") {
        try {
            await apiFetch(`/api/consultations/proposals/${id}/${action}`, { method: "POST" });
            await refresh();
        } catch (e: any) {
            alert(e.message);
        }
    }

    if (loading) return <div className="text-center py-12 text-gray-500">Loading…</div>;
    if (error) return <div className="text-center py-12 text-red-500">{error}</div>;
    if (!chat) return null;

    const isOpen = chat.status === "open";
    const isConsultant = me?.user_type === "consultant";
    const pending = proposals.filter((p) => p.status === "pending");
    const accepted = proposals.find((p) => p.status === "accepted");

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">
                        Chat with {chat.other_party_name ?? "—"}
                    </h1>
                    {chat.other_party_email && (
                        <p className="text-sm text-gray-500">{chat.other_party_email}</p>
                    )}
                </div>
                <Link href={backHref} className="text-sm text-blue-600 hover:underline">
                    ← Back
                </Link>
            </div>

            {accepted && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center justify-between gap-3">
                    <p className="text-sm text-green-800">
                        ✅ Consultation booked for{" "}
                        {new Date(accepted.start_at).toLocaleString([], {
                            dateStyle: "medium",
                            timeStyle: "short",
                        })}
                    </p>
                    <Link href="/appointments" className="text-sm font-medium text-green-700 underline">
                        View appointments →
                    </Link>
                </div>
            )}

            <div className="grid gap-4 lg:grid-cols-3">
                {/* Chat */}
                <div className="lg:col-span-2 flex flex-col bg-white rounded-xl shadow" style={{ minHeight: "60vh" }}>
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
                                    <div className={`max-w-[78%] rounded-2xl px-4 py-2 text-sm ${mine ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-900"}`}>
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
                    {isOpen ? (
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
                    ) : (
                        <div className="px-4 py-2 bg-gray-50 border-t text-xs text-gray-500 text-center">
                            This chat is closed.
                        </div>
                    )}
                </div>

                {/* Proposals sidebar */}
                <div className="space-y-3">
                    {/* Propose a time (consultant only) */}
                    {isOpen && isConsultant && (
                        <form onSubmit={handlePropose} className="bg-white rounded-xl shadow p-4 space-y-2">
                            <h3 className="text-sm font-semibold text-gray-900">📅 Propose a time</h3>
                            <label className="block text-xs text-gray-500">Start</label>
                            <input
                                type="datetime-local"
                                value={proposeStart}
                                onChange={(e) => setProposeStart(e.target.value)}
                                className="block w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs"
                            />
                            <label className="block text-xs text-gray-500">End</label>
                            <input
                                type="datetime-local"
                                value={proposeEnd}
                                onChange={(e) => setProposeEnd(e.target.value)}
                                className="block w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs"
                            />
                            <button
                                type="submit"
                                disabled={proposing || !proposeStart || !proposeEnd}
                                className="w-full text-xs bg-blue-600 text-white rounded py-1.5 hover:bg-blue-700 disabled:opacity-50 font-medium"
                            >
                                {proposing ? "…" : "Propose"}
                            </button>
                        </form>
                    )}

                    {/* Pending proposals */}
                    {pending.length > 0 && (
                        <div className="bg-white rounded-xl shadow p-4 space-y-3">
                            <h3 className="text-sm font-semibold text-gray-900">Pending proposals</h3>
                            {pending.map((p) => {
                                const mine = p.proposed_by_user_id === me?.id;
                                return (
                                    <div key={p.id} className="border border-yellow-200 bg-yellow-50 rounded-lg p-3 space-y-2">
                                        <p className="text-xs font-medium text-yellow-800">
                                            {new Date(p.start_at).toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" })}{" "}
                                            · {new Date(p.start_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                            {" – "}
                                            {new Date(p.end_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                        </p>
                                        {mine ? (
                                            <button
                                                onClick={() => handleProposalAction(p.id, "cancel")}
                                                className="w-full text-xs bg-gray-100 text-gray-700 rounded py-1.5 hover:bg-gray-200"
                                            >
                                                Cancel proposal
                                            </button>
                                        ) : (
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => handleProposalAction(p.id, "accept")}
                                                    className="flex-1 text-xs bg-green-600 text-white rounded py-1.5 hover:bg-green-700 font-medium"
                                                >
                                                    ✓ Accept &amp; Book
                                                </button>
                                                <button
                                                    onClick={() => handleProposalAction(p.id, "reject")}
                                                    className="flex-1 text-xs bg-red-100 text-red-700 rounded py-1.5 hover:bg-red-200"
                                                >
                                                    ✕ Reject
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}

                    {/* History */}
                    {proposals.filter((p) => p.status !== "pending").length > 0 && (
                        <div className="bg-white rounded-xl shadow p-4">
                            <h3 className="text-sm font-semibold text-gray-900 mb-2">Proposal history</h3>
                            {proposals
                                .filter((p) => p.status !== "pending")
                                .map((p) => (
                                    <div key={p.id} className="flex items-center justify-between text-xs py-1.5 border-b last:border-0">
                                        <span className="text-gray-600">
                                            {new Date(p.start_at).toLocaleDateString()}
                                        </span>
                                        <span className={`px-2 py-0.5 rounded-full font-medium ${p.status === "accepted" ? "bg-green-100 text-green-700" : p.status === "rejected" ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-600"}`}>
                                            {p.status}
                                        </span>
                                    </div>
                                ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
