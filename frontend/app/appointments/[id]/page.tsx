"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type {
    AppointmentDetailsResponse,
    ChatMessageRead,
    SessionNoteRead,
} from "@/lib/types";

export default function AppointmentDetailsPage() {
    const params = useParams();
    const router = useRouter();
    const appointmentId = params.id as string;

    const [details, setDetails] = useState<AppointmentDetailsResponse | null>(null);
    const [chatHistory, setChatHistory] = useState<ChatMessageRead[]>([]);
    const [sessionNotes, setSessionNotes] = useState<SessionNoteRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [adopting, setAdopting] = useState<string | null>(null);

    useEffect(() => {
        async function loadDetails() {
            try {
                const [detailsRes, chatRes, notesRes] = await Promise.allSettled([
                    apiFetch<AppointmentDetailsResponse>(`/api/appointments/${appointmentId}/details`),
                    apiFetch<ChatMessageRead[]>(`/api/session/appointments/${appointmentId}/messages`),
                    apiFetch<SessionNoteRead[]>(`/api/session/appointments/${appointmentId}/notes`),
                ]);

                if (detailsRes.status === "fulfilled") {
                    setDetails(detailsRes.value);
                }

                if (chatRes.status === "fulfilled") {
                    setChatHistory(chatRes.value);
                }

                if (notesRes.status === "fulfilled") {
                    // Filter to only show notes visible to user
                    setSessionNotes(notesRes.value.filter((note) => note.is_visible_to_user));
                }
            } catch (error) {
                console.error("Failed to load appointment details:", error);
            } finally {
                setLoading(false);
            }
        }

        loadDetails();
    }, [appointmentId]);

    async function adoptGoal() {
        if (!details?.goal) return;

        setAdopting("goal");
        try {
            await apiFetch(`/api/goal/${details.goal.id}/activate`, {
                method: "PUT",
            });
            alert("Goal activated successfully!");
        } catch (error: any) {
            alert(`Failed to activate goal: ${error.message}`);
        } finally {
            setAdopting(null);
        }
    }

    async function adoptTarget() {
        if (!details?.nutrition_target) return;

        setAdopting("target");
        try {
            await apiFetch(`/api/nutrition-target/${details.nutrition_target.id}/activate`, {
                method: "PUT",
            });
            alert("Nutrition target activated successfully!");
        } catch (error: any) {
            alert(`Failed to activate target: ${error.message}`);
        } finally {
            setAdopting(null);
        }
    }

    if (loading) {
        return <div className="text-center py-12">Loading...</div>;
    }

    if (!details) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500">Appointment not found</p>
                <Link href="/appointments" className="text-blue-600 hover:text-blue-500 mt-2 inline-block">
                    ← Back to appointments
                </Link>
            </div>
        );
    }

    const { appointment, goal, nutrition_target, consultant } = details;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <Link href="/appointments" className="text-sm text-blue-600 hover:text-blue-500">
                    ← Back to appointments
                </Link>
                <h1 className="text-3xl font-bold text-gray-900 mt-2">Appointment Details</h1>
                <p className="mt-1 text-sm text-gray-600">
                    {new Date(appointment.scheduled_start_at).toLocaleDateString()}
                </p>
            </div>

            {/* Consultant Info */}
            {consultant && (
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-2">Consultant</h2>
                    <div>
                        <p className="text-base font-medium text-gray-900">{consultant.full_name || consultant.username}</p>
                        <p className="text-sm text-gray-600">{consultant.email}</p>
                    </div>
                </div>
            )}

            {/* Goal Section */}
            {goal && (
                <div className="bg-white shadow rounded-lg p-6">
                    <div className="flex items-start justify-between">
                        <div className="flex-1">
                            <h2 className="text-lg font-semibold text-gray-900 mb-3">
                                Goal Created by Consultant {goal.active ? "(Active)" : "(Suggested)"}
                            </h2>
                            <div className="space-y-2">
                                <p className="text-sm">
                                    <span className="font-medium">Goal Type:</span>{" "}
                                    <span className="capitalize">{goal.goal_type}</span>
                                </p>
                                {goal.target_delta_kg && (
                                    <p className="text-sm">
                                        <span className="font-medium">Target Change:</span> {goal.target_delta_kg} kg
                                    </p>
                                )}
                                {goal.duration_days && (
                                    <p className="text-sm">
                                        <span className="font-medium">Duration:</span> {goal.duration_days} days
                                    </p>
                                )}
                                {goal.start_date && (
                                    <p className="text-sm">
                                        <span className="font-medium">Start Date:</span>{" "}
                                        {new Date(goal.start_date).toLocaleDateString()}
                                    </p>
                                )}
                            </div>
                        </div>
                        {!goal.active && (
                            <button
                                onClick={adoptGoal}
                                disabled={adopting === "goal"}
                                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
                            >
                                {adopting === "goal" ? "Adopting..." : "Adopt This Goal"}
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Nutrition Target Section */}
            {nutrition_target && (
                <div className="bg-white shadow rounded-lg p-6">
                    <div className="flex items-start justify-between">
                        <div className="flex-1">
                            <h2 className="text-lg font-semibold text-gray-900 mb-3">
                                Nutrition Target Created by Consultant {nutrition_target.active ? "(Active)" : "(Suggested)"}
                            </h2>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-sm font-medium text-gray-700">Calories</p>
                                    <p className="text-2xl font-bold text-gray-900">{nutrition_target.calories_kcal} kcal</p>
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-gray-700">Protein</p>
                                    <p className="text-2xl font-bold text-gray-900">{nutrition_target.protein_g} g</p>
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-gray-700">Carbs</p>
                                    <p className="text-2xl font-bold text-gray-900">{nutrition_target.carbs_g} g</p>
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-gray-700">Fat</p>
                                    <p className="text-2xl font-bold text-gray-900">{nutrition_target.fat_g} g</p>
                                </div>
                            </div>
                        </div>
                        {!nutrition_target.active && (
                            <button
                                onClick={adoptTarget}
                                disabled={adopting === "target"}
                                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
                            >
                                {adopting === "target" ? "Adopting..." : "Adopt This Target"}
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Chat History */}
            {chatHistory.length > 0 && (
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Chat History</h2>
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                        {chatHistory.map((msg) => (
                            <div key={msg.id} className="border-l-4 border-blue-500 pl-4 py-2">
                                <p className="text-xs text-gray-500">
                                    {new Date(msg.sent_at).toLocaleString()}
                                </p>
                                <p className="text-sm text-gray-900 mt-1">{msg.message}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Session Notes */}
            {sessionNotes.length > 0 && (
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Session Notes</h2>
                    <div className="space-y-4">
                        {sessionNotes.map((note) => (
                            <div key={note.id} className="bg-gray-50 rounded-lg p-4">
                                <p className="text-xs text-gray-500 mb-2">
                                    {new Date(note.created_at).toLocaleString()}
                                </p>
                                <p className="text-sm text-gray-900 whitespace-pre-wrap">{note.note}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {!goal && !nutrition_target && chatHistory.length === 0 && sessionNotes.length === 0 && (
                <div className="bg-white shadow rounded-lg p-6 text-center">
                    <p className="text-gray-500">No additional details available for this appointment.</p>
                </div>
            )}
        </div>
    );
}
