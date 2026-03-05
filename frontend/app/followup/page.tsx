"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { FollowUpRoomRead } from "@/lib/types";

export default function UserFollowUpPage() {
    const [rooms, setRooms] = useState<FollowUpRoomRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [cancelling, setCancelling] = useState<string | null>(null);

    useEffect(() => {
        apiFetch<FollowUpRoomRead[]>("/api/followup/rooms")
            .then(setRooms)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    async function handleCancel(roomId: string) {
        if (!confirm("Cancel this follow-up? Your consultant will be notified.")) return;
        setCancelling(roomId);
        try {
            const updated = await apiFetch<FollowUpRoomRead>(`/api/followup/rooms/${roomId}/cancel`, {
                method: "POST",
            });
            setRooms((prev) => prev.map((r) => (r.id === roomId ? updated : r)));
        } catch (e: any) {
            alert(e.message);
        } finally {
            setCancelling(null);
        }
    }

    if (loading)
        return <div className="text-center py-12 text-gray-500">Loading follow-ups…</div>;

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Follow-up Rooms</h1>
                <p className="mt-1 text-sm text-gray-500">
                    Your consultant starts follow-up rooms from sessions. Use them to view session history
                    and schedule next appointments.
                </p>
            </div>

            {rooms.length === 0 ? (
                <div className="text-center py-16 bg-white rounded-xl shadow">
                    <div className="text-5xl mb-3">💬</div>
                    <p className="text-gray-600 font-semibold">No follow-up rooms yet.</p>
                    <p className="text-sm text-gray-400 mt-1">
                        Your consultant can start one during or after a session.
                    </p>
                </div>
            ) : (
                <div className="space-y-3">
                    {rooms.map((room) => (
                        <div
                            key={room.id}
                            className="bg-white rounded-xl shadow border border-gray-100 p-5 flex items-center justify-between gap-4"
                        >
                            <Link
                                href={`/followup/${room.id}`}
                                className="flex items-center gap-4 flex-1 min-w-0"
                            >
                                <div className="w-11 h-11 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-xl shrink-0">
                                    {(room.other_party_name?.[0] ?? "?").toUpperCase()}
                                </div>
                                <div className="min-w-0">
                                    <p className="font-semibold text-gray-900 truncate">
                                        {room.other_party_name ?? "Consultant"}
                                    </p>
                                    {room.other_party_email && (
                                        <p className="text-xs text-gray-500 truncate">{room.other_party_email}</p>
                                    )}
                                    <span
                                        className={`inline-block mt-1 text-[10px] px-2 py-0.5 rounded-full font-medium ${room.status === "active"
                                            ? "bg-green-100 text-green-700"
                                            : "bg-red-100 text-red-600"
                                            }`}
                                    >
                                        {room.status === "active"
                                            ? "Active"
                                            : `Cancelled by ${room.cancelled_by_name ?? "unknown"}`}
                                    </span>
                                </div>
                            </Link>

                            <div className="flex items-center gap-2 shrink-0">
                                {room.last_message_at && (
                                    <span className="text-xs text-gray-400 hidden sm:block">
                                        {new Date(room.last_message_at).toLocaleDateString()}
                                    </span>
                                )}
                                <Link
                                    href={`/followup/${room.id}`}
                                    className="text-sm text-blue-600 font-medium hover:underline"
                                >
                                    Open →
                                </Link>
                                {room.status === "active" && (
                                    <button
                                        onClick={() => handleCancel(room.id)}
                                        disabled={cancelling === room.id}
                                        className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
                                    >
                                        {cancelling === room.id ? "…" : "Cancel"}
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
