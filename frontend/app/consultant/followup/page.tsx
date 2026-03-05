"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { FollowUpRoomRead } from "@/lib/types";

export default function ConsultantFollowUpPage() {
    const [rooms, setRooms] = useState<FollowUpRoomRead[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchRooms = async () => {
            try {
                const data = await apiFetch<FollowUpRoomRead[]>("/api/followup/rooms");
                setRooms(data);
            } catch (error) {
                console.error(error);
            } finally {
                setLoading(false);
            }
        };
        fetchRooms();
    }, []);

    if (loading)
        return <div className="text-center py-12 text-gray-500">Loading follow-ups…</div>;

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Follow-up Rooms</h1>
                <p className="mt-1 text-sm text-gray-500">
                    Start a follow-up from within an active session. Click a room to view patient
                    details, session history, and schedule the next appointment.
                </p>
            </div>

            {rooms.length === 0 ? (
                <div className="text-center py-16 bg-white rounded-xl shadow">
                    <div className="text-5xl mb-3">💬</div>
                    <p className="text-gray-600 font-semibold">No follow-up rooms yet.</p>
                    <p className="text-sm text-gray-400 mt-1">
                        Click <strong>"Start Follow-up"</strong> inside an active session to create one.
                    </p>
                </div>
            ) : (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {rooms.map((room) => (
                        <Link
                            key={room.id}
                            href={`/consultant/followup/${room.id}`}
                            className="block bg-white rounded-xl shadow hover:shadow-lg transition-shadow p-5 border border-gray-100"
                        >
                            {/* Avatar + name */}
                            <div className="flex items-center gap-3 mb-3">
                                <div className="w-11 h-11 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-xl">
                                    {(room.other_party_name?.[0] ?? "?").toUpperCase()}
                                </div>
                                <div className="min-w-0">
                                    <p className="font-semibold text-gray-900 truncate">
                                        {room.other_party_name ?? "Patient"}
                                    </p>
                                    {room.other_party_email && (
                                        <p className="text-xs text-gray-500 truncate">{room.other_party_email}</p>
                                    )}
                                </div>
                            </div>

                            {/* Status */}
                            <div className="flex items-center justify-between text-xs">
                                <span
                                    className={`px-2 py-0.5 rounded-full font-medium ${room.status === "active"
                                        ? "bg-green-100 text-green-700"
                                        : "bg-red-100 text-red-600"
                                        }`}
                                >
                                    {room.status === "active" ? "Active" : "Cancelled"}
                                </span>
                                {room.status === "closed" && room.cancelled_by_name && (
                                    <span className="text-gray-400">Cancelled by {room.cancelled_by_name}</span>
                                )}
                                {room.last_message_at && (
                                    <span className="text-gray-400">
                                        {new Date(room.last_message_at).toLocaleDateString()}
                                    </span>
                                )}
                            </div>

                            <p className="mt-3 text-xs text-blue-600 font-medium">View Details →</p>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
