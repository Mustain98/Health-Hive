"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { AppointmentRead, AppointmentApplicationRead } from "@/lib/types";

export default function AppointmentsPage() {
    const [appointments, setAppointments] = useState<AppointmentRead[]>([]);
    const [applications, setApplications] = useState<AppointmentApplicationRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<"appointments" | "applications">("appointments");

    useEffect(() => {
        async function loadData() {
            try {
                const [appts, apps] = await Promise.all([
                    apiFetch<AppointmentRead[]>("/api/appointments/me"),
                    apiFetch<AppointmentApplicationRead[]>("/api/appointments/applications/me"),
                ]);

                setAppointments(appts);
                setApplications(apps);
            } catch (error) {
                console.error("Failed to load appointments:", error);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, []);

    if (loading) {
        return <div className="text-center py-12">Loading...</div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">My Appointments</h1>
                    <p className="mt-2 text-sm text-gray-600">
                        View your scheduled appointments and pending applications
                    </p>
                </div>
                <Link
                    href="/consultants"
                    className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                    Find Consultants
                </Link>
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-200">
                <nav className="-mb-px flex space-x-8">
                    <button
                        onClick={() => setActiveTab("appointments")}
                        className={`${activeTab === "appointments"
                                ? "border-blue-500 text-blue-600"
                                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                    >
                        Scheduled Appointments ({appointments.length})
                    </button>
                    <button
                        onClick={() => setActiveTab("applications")}
                        className={`${activeTab === "applications"
                                ? "border-blue-500 text-blue-600"
                                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
                    >
                        Applications ({applications.length})
                    </button>
                </nav>
            </div>

            {/* Content */}
            {activeTab === "appointments" ? (
                <div className="space-y-4">
                    {appointments.length === 0 ? (
                        <div className="text-center py-12 bg-white rounded-lg shadow">
                            <p className="text-gray-500">No scheduled appointments</p>
                            <Link
                                href="/consultants"
                                className="text-blue-600 hover:text-blue-500 mt-2 inline-block"
                            >
                                Find a consultant →
                            </Link>
                        </div>
                    ) : (
                        appointments.map((appointment) => (
                            <div key={appointment.id} className="bg-white shadow rounded-lg p-6">
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <div className="flex items-center space-x-2">
                                            <h3 className="text-lg font-medium text-gray-900">
                                                Appointment #{appointment.id}
                                            </h3>
                                            <span
                                                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${appointment.status === "scheduled"
                                                        ? "bg-blue-100 text-blue-800"
                                                        : appointment.status === "completed"
                                                            ? "bg-green-100 text-green-800"
                                                            : "bg-gray-100 text-gray-800"
                                                    }`}
                                            >
                                                {appointment.status}
                                            </span>
                                        </div>
                                        <div className="mt-2 space-y-1">
                                            <p className="text-sm text-gray-600">
                                                <span className="font-medium">Start:</span>{" "}
                                                {new Date(appointment.scheduled_start_at).toLocaleString()}
                                            </p>
                                            <p className="text-sm text-gray-600">
                                                <span className="font-medium">End:</span>{" "}
                                                {new Date(appointment.scheduled_end_at).toLocaleString()}
                                            </p>
                                        </div>
                                    </div>
                                    {appointment.status === "scheduled" && (
                                        <Link
                                            href={`/session/${appointment.id}`}
                                            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                                        >
                                            Join Session
                                        </Link>
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            ) : (
                <div className="space-y-4">
                    {applications.length === 0 ? (
                        <div className="text-center py-12 bg-white rounded-lg shadow">
                            <p className="text-gray-500">No pending applications</p>
                        </div>
                    ) : (
                        applications.map((app) => (
                            <div key={app.id} className="bg-white shadow rounded-lg p-6">
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <div className="flex items-center space-x-2">
                                            <h3 className="text-lg font-medium text-gray-900">
                                                Application #{app.id}
                                            </h3>
                                            <span
                                                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${app.status === "submitted"
                                                        ? "bg-yellow-100 text-yellow-800"
                                                        : app.status === "accepted"
                                                            ? "bg-green-100 text-green-800"
                                                            : "bg-red-100 text-red-800"
                                                    }`}
                                            >
                                                {app.status}
                                            </span>
                                        </div>
                                        <p className="mt-2 text-sm text-gray-600">
                                            <span className="font-medium">Submitted:</span>{" "}
                                            {new Date(app.created_at).toLocaleDateString()}
                                        </p>
                                        {app.note_from_user && (
                                            <p className="mt-2 text-sm text-gray-700">
                                                <span className="font-medium">Your message:</span> {app.note_from_user}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}
