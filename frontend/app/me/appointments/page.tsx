"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { AppointmentRead } from "@/lib/types";

export default function MyAppointmentsPage() {
    const [appointments, setAppointments] = useState<AppointmentRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [message, setMessage] = useState<string | null>(null);

    useEffect(() => {
        loadAppointments();
    }, []);

    function fixDate(d: string): string {
        return d.endsWith("Z") ? d : d + "Z";
    }

    async function loadAppointments() {
        try {
            const raw = await apiFetch<AppointmentRead[]>("/api/appointments/me");
            const data = raw.map(a => ({
                ...a,
                scheduled_start_at: fixDate(a.scheduled_start_at),
                scheduled_end_at: fixDate(a.scheduled_end_at),
                created_at: fixDate(a.created_at),
                updated_at: fixDate(a.updated_at),
            }));
            setAppointments(data);
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    }

    async function handleCancel(appointmentId: number) {
        if (!confirm("Are you sure you want to cancel this appointment?")) return;

        setMessage(null);
        try {
            await apiFetch(`/api/appointments/appointments/${appointmentId}/cancel`, {
                method: "POST",
            });
            setMessage("Appointment cancelled successfully");
            await loadAppointments();
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        }
    }

    function getStatusColor(status: string): string {
        switch (status) {
            case "scheduled":
                return "bg-green-100 text-green-800";
            case "completed":
                return "bg-blue-100 text-blue-800";
            case "cancelled":
                return "bg-gray-100 text-gray-800";
            case "no_show":
                return "bg-red-100 text-red-800";
            default:
                return "bg-gray-100 text-gray-800";
        }
    }

    function getStatusLabel(status: string): string {
        return status.replace("_", " ").split(" ").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
    }

    if (loading) {
        return <div className="text-center py-12">Loading appointments...</div>;
    }

    return (
        <div className="max-w-4xl mx-auto p-6 space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">My Appointments</h1>
                <p className="mt-2 text-sm text-gray-600">
                    View and manage your scheduled appointments
                </p>
            </div>

            {message && (
                <div className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                    <p className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                        {message}
                    </p>
                </div>
            )}

            {appointments.length === 0 ? (
                <div className="bg-white rounded-lg shadow p-12 text-center">
                    <p className="text-gray-500 mb-4">No appointments yet</p>
                    <Link
                        href="/consultants"
                        className="inline-block px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                    >
                        Browse Consultants
                    </Link>
                </div>
            ) : (
                <div className="space-y-4">
                    {appointments.map((appt) => {
                        const startDate = new Date(appt.scheduled_start_at);
                        const endDate = new Date(appt.scheduled_end_at);
                        const duration = Math.round((endDate.getTime() - startDate.getTime()) / 60000);
                        const isPast = endDate < new Date();
                        const isUpcoming = startDate > new Date() && appt.status === "scheduled";

                        return (
                            <div key={appt.id} className="bg-white rounded-lg shadow p-6">
                                <div className="flex items-start justify-between mb-4">
                                    <div>
                                        <h3 className="text-lg font-semibold text-gray-900">
                                            Appointment #{appt.id}
                                        </h3>
                                        <p className="text-sm text-gray-600">
                                            Consultant User #{appt.consultant_user_id}
                                        </p>
                                    </div>
                                    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(appt.status)}`}>
                                        {getStatusLabel(appt.status)}
                                    </span>
                                </div>

                                <div className="space-y-2 mb-4">
                                    <div className="flex items-center gap-2 text-sm">
                                        <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                        </svg>
                                        <span className="font-medium text-gray-700">Date:</span>
                                        <span className="text-gray-900">{startDate.toLocaleDateString()}</span>
                                    </div>

                                    <div className="flex items-center gap-2 text-sm">
                                        <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        <span className="font-medium text-gray-700">Time:</span>
                                        <span className="text-gray-900">
                                            {startDate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} – {endDate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                        </span>
                                        <span className="text-gray-500">({duration} mins)</span>
                                    </div>
                                </div>

                                <div className="flex gap-3 pt-3 border-t border-gray-200">
                                    {isUpcoming && (
                                        <>
                                            <Link
                                                href={`/session/${appt.id}`}
                                                className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                                            >
                                                Join Session
                                            </Link>
                                            <button
                                                onClick={() => handleCancel(appt.id)}
                                                className="px-4 py-2 text-sm font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200"
                                            >
                                                Cancel Appointment
                                            </button>
                                        </>
                                    )}

                                    {appt.status === "completed" && (
                                        <Link
                                            href={`/session/${appt.id}`}
                                            className="text-sm font-medium text-blue-600 hover:text-blue-700"
                                        >
                                            View Session Details →
                                        </Link>
                                    )}

                                    {appt.status === "cancelled" && (
                                        <p className="text-sm text-gray-600">This appointment was cancelled</p>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
