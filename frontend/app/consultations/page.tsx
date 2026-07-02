"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { ConsultationRequestRead } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    accepted: "bg-green-100 text-green-700",
    declined: "bg-red-100 text-red-600",
};

export default function MyConsultationsPage() {
    const [requests, setRequests] = useState<ConsultationRequestRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function load() {
            try {
                const data = await apiFetch<ConsultationRequestRead[]>("/api/consultations/requests/me");
                setRequests(data);
            } catch (e: any) {
                setError(e.message || "Failed to load requests");
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    if (loading) return <div className="text-center py-12 text-gray-500">Loading…</div>;
    if (error) return <div className="text-center py-12 text-red-500">{error}</div>;

    return (
        <div className="max-w-3xl mx-auto p-6 space-y-4">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">My Consultation Requests</h1>
                <Link href="/consultants" className="text-sm text-blue-600 hover:underline">
                    Find a consultant →
                </Link>
            </div>

            {requests.length === 0 ? (
                <div className="bg-white rounded-xl shadow p-8 text-center">
                    <p className="text-gray-400 text-sm">
                        You haven't requested any consultations yet.
                    </p>
                    <Link href="/consultants" className="text-sm text-blue-600 hover:underline mt-2 inline-block">
                        Browse consultants
                    </Link>
                </div>
            ) : (
                <div className="space-y-3">
                    {requests.map((r) => (
                        <div key={r.id} className="bg-white rounded-lg shadow p-5">
                            <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <p className="text-sm font-semibold text-gray-900">
                                        {r.other_party_name ?? "Consultant"}
                                    </p>
                                    <p className="text-sm text-gray-600 mt-1 whitespace-pre-line">{r.issue}</p>
                                    <p className="text-[11px] text-gray-400 mt-2">
                                        {new Date(r.created_at).toLocaleString()}
                                    </p>
                                </div>
                                <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_STYLES[r.status] ?? "bg-gray-100 text-gray-600"}`}>
                                    {r.status}
                                </span>
                            </div>

                            <div className="mt-3">
                                {r.status === "accepted" && r.chat_id ? (
                                    <Link
                                        href={`/consultations/${r.chat_id}`}
                                        className="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                                    >
                                        💬 Open Chat
                                    </Link>
                                ) : r.status === "pending" ? (
                                    <p className="text-xs text-gray-500">
                                        Waiting for the consultant to reply…
                                    </p>
                                ) : (
                                    <p className="text-xs text-gray-500">
                                        This request was declined.
                                    </p>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
