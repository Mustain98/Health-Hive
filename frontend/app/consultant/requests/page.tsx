"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { ConsultationRequestRead, ConsultationChatRead } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    accepted: "bg-green-100 text-green-700",
    declined: "bg-red-100 text-red-600",
};

export default function ConsultantRequestsPage() {
    const router = useRouter();
    const [requests, setRequests] = useState<ConsultationRequestRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // reply state
    const [replyingId, setReplyingId] = useState<string | null>(null);
    const [replyText, setReplyText] = useState("");
    const [busy, setBusy] = useState(false);

    useEffect(() => {
        load();
    }, []);

    async function load() {
        setLoading(true);
        try {
            const data = await apiFetch<ConsultationRequestRead[]>("/api/consultations/requests/incoming");
            setRequests(data);
        } catch (e: any) {
            setError(e.message || "Failed to load requests");
        } finally {
            setLoading(false);
        }
    }

    async function handleReply(id: string) {
        if (!replyText.trim() || busy) return;
        setBusy(true);
        try {
            const chat = await apiFetch<ConsultationChatRead>(
                `/api/consultations/requests/${id}/reply`,
                { method: "POST", body: { message: replyText.trim() } }
            );
            router.push(`/consultant/consultations/${chat.id}`);
        } catch (e: any) {
            alert(e.message);
            setBusy(false);
        }
    }

    async function handleDecline(id: string) {
        if (!confirm("Decline this request?") || busy) return;
        setBusy(true);
        try {
            await apiFetch(`/api/consultations/requests/${id}/decline`, { method: "POST" });
            await load();
        } catch (e: any) {
            alert(e.message);
        } finally {
            setBusy(false);
        }
    }

    if (loading) return <div className="text-center py-12 text-gray-500">Loading…</div>;
    if (error) return <div className="text-center py-12 text-red-500">{error}</div>;

    const pending = requests.filter((r) => r.status === "pending");
    const others = requests.filter((r) => r.status !== "pending");

    return (
        <div className="max-w-3xl mx-auto p-6 space-y-6">
            <h1 className="text-2xl font-bold text-gray-900">Consultation Requests</h1>

            <section className="space-y-3">
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Pending</h2>
                {pending.length === 0 ? (
                    <p className="text-sm text-gray-400">No pending requests.</p>
                ) : (
                    pending.map((r) => (
                        <div key={r.id} className="bg-white rounded-lg shadow p-5 space-y-3">
                            <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <p className="text-sm font-semibold text-gray-900">{r.other_party_name ?? "User"}</p>
                                    {r.other_party_email && (
                                        <p className="text-xs text-gray-500">{r.other_party_email}</p>
                                    )}
                                    <p className="text-sm text-gray-700 mt-2 whitespace-pre-line">{r.issue}</p>
                                    <p className="text-[11px] text-gray-400 mt-2">{new Date(r.created_at).toLocaleString()}</p>
                                </div>
                                <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_STYLES[r.status]}`}>
                                    {r.status}
                                </span>
                            </div>

                            {replyingId === r.id ? (
                                <div className="space-y-2">
                                    <textarea
                                        rows={3}
                                        value={replyText}
                                        onChange={(e) => setReplyText(e.target.value)}
                                        placeholder="Write a reply to start the chat…"
                                        className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                    />
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleReply(r.id)}
                                            disabled={busy || !replyText.trim()}
                                            className="px-4 py-1.5 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                                        >
                                            {busy ? "…" : "Send & Open Chat"}
                                        </button>
                                        <button
                                            onClick={() => { setReplyingId(null); setReplyText(""); }}
                                            className="px-4 py-1.5 text-sm rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200"
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => { setReplyingId(r.id); setReplyText(""); }}
                                        className="px-4 py-1.5 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                                    >
                                        Reply
                                    </button>
                                    <button
                                        onClick={() => handleDecline(r.id)}
                                        disabled={busy}
                                        className="px-4 py-1.5 text-sm rounded-md bg-red-50 text-red-600 border border-red-200 hover:bg-red-100 disabled:opacity-50"
                                    >
                                        Decline
                                    </button>
                                </div>
                            )}
                        </div>
                    ))
                )}
            </section>

            {others.length > 0 && (
                <section className="space-y-3">
                    <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Handled</h2>
                    {others.map((r) => (
                        <div key={r.id} className="bg-white rounded-lg shadow p-4 flex items-start justify-between gap-3">
                            <div className="min-w-0">
                                <p className="text-sm font-medium text-gray-900">{r.other_party_name ?? "User"}</p>
                                <p className="text-sm text-gray-600 mt-1 whitespace-pre-line">{r.issue}</p>
                            </div>
                            <div className="shrink-0 text-right space-y-1">
                                <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_STYLES[r.status]}`}>
                                    {r.status}
                                </span>
                                {r.status === "accepted" && r.chat_id && (
                                    <div>
                                        <Link href={`/consultant/consultations/${r.chat_id}`} className="text-xs text-blue-600 hover:underline">
                                            Open chat →
                                        </Link>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </section>
            )}
        </div>
    );
}
