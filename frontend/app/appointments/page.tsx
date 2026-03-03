"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { AppointmentRead, AppointmentApplicationRead, AppointmentDetailsResponse } from "@/lib/types";

/** Ensure a bare datetime string from the backend is treated as UTC */
function fixUtc(d: string): string {
    return d && !d.endsWith("Z") ? d + "Z" : d;
}

function fixAppt(a: AppointmentRead): AppointmentRead {
    return {
        ...a,
        scheduled_start_at: fixUtc(a.scheduled_start_at),
        scheduled_end_at: fixUtc(a.scheduled_end_at),
        created_at: fixUtc(a.created_at),
        updated_at: fixUtc(a.updated_at),
    };
}

export default function AppointmentsPage() {
    const [appointments, setAppointments] = useState<AppointmentRead[]>([]);
    const [filteredAppointments, setFilteredAppointments] = useState<AppointmentRead[]>([]);
    const [applications, setApplications] = useState<AppointmentApplicationRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<"appointments" | "applications">("appointments");
    const [filterDate, setFilterDate] = useState("");
    const [filterConsultant, setFilterConsultant] = useState("");
    const [filterStatus, setFilterStatus] = useState<string>("all");

    useEffect(() => {
        async function loadData() {
            try {
                const [appts, apps] = await Promise.all([
                    apiFetch<AppointmentRead[]>("/api/appointments/me"),
                    apiFetch<AppointmentApplicationRead[]>("/api/appointments/applications/me"),
                ]);

                setAppointments(appts.map(fixAppt));
                setFilteredAppointments(appts.map(fixAppt));
                setApplications(apps);
            } catch (error) {
                console.error("Failed to load appointments:", error);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, []);

    // Apply filters
    useEffect(() => {
        let filtered = [...appointments];

        if (filterDate) {
            filtered = filtered.filter((appt) =>
                appt.scheduled_start_at.startsWith(filterDate)
            );
        }

        if (filterConsultant) {
            const term = filterConsultant.toLowerCase();
            filtered = filtered.filter((appt) => {
                const name = appt.consultant_name || appt.consultant?.display_name || "";
                const email = appt.consultant_email || "";
                return name.toLowerCase().includes(term) || email.toLowerCase().includes(term);
            });
        }

        if (filterStatus !== "all") {
            filtered = filtered.filter((appt) => appt.status === filterStatus);
        }

        setFilteredAppointments(filtered);
    }, [filterDate, filterConsultant, filterStatus, appointments]);



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
                <div className=" space-y-4">
                    {/* Filters */}
                    <div className="bg-white shadow rounded-lg p-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Filter by Date
                                </label>
                                <input
                                    type="date"
                                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                    value={filterDate}
                                    onChange={(e) => setFilterDate(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Filter by Consultant
                                </label>
                                <input
                                    type="text"
                                    placeholder="Consultant name or email..."
                                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                    value={filterConsultant}
                                    onChange={(e) => setFilterConsultant(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Filter by Status
                                </label>
                                <select
                                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                    value={filterStatus}
                                    onChange={(e) => setFilterStatus(e.target.value)}
                                >
                                    <option value="all">All Statuses</option>
                                    <option value="scheduled">Scheduled</option>
                                    <option value="completed">Completed</option>
                                    <option value="cancelled">Cancelled</option>
                                </select>
                            </div>
                        </div>
                        {(filterDate || filterConsultant || filterStatus !== "all") && (
                            <button
                                onClick={() => {
                                    setFilterDate("");
                                    setFilterConsultant("");
                                    setFilterStatus("all");
                                }}
                                className="mt-3 text-sm text-blue-600 hover:text-blue-500"
                            >
                                Clear all filters
                            </button>
                        )}
                    </div>

                    {/* Appointments List */}
                    {filteredAppointments.length === 0 ? (
                        <div className="text-center py-12 bg-white rounded-lg shadow">
                            <p className="text-gray-500">
                                {appointments.length === 0
                                    ? "No scheduled appointments"
                                    : "No appointments match your filters"}
                            </p>
                            {appointments.length === 0 && (
                                <Link
                                    href="/consultants"
                                    className="text-blue-600 hover:text-blue-500 mt-2 inline-block"
                                >
                                    Find a consultant →
                                </Link>
                            )}
                        </div>
                    ) : (
                        filteredAppointments.map((appointment) => (
                            <div key={appointment.id} className="bg-white shadow rounded-lg p-6">
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        {/* Consultant Info */}
                                        <div className="mb-3 pb-3 border-b border-gray-200">
                                            <h3 className="text-lg font-semibold text-gray-900">
                                                {appointment.consultant_name
                                                    || appointment.consultant?.display_name
                                                    || "Consultant"}
                                            </h3>
                                            {appointment.consultant_email && (
                                                <p className="text-sm text-gray-500 mt-0.5">
                                                    ✉ {appointment.consultant_email}
                                                </p>
                                            )}
                                            {appointment.consultant?.specialties && (
                                                <p className="text-sm text-gray-600 mt-1">
                                                    {appointment.consultant.specialties}
                                                </p>
                                            )}
                                            {appointment.consultant?.is_verified && (
                                                <span className="mt-1 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                                    ✓ Verified
                                                </span>
                                            )}
                                        </div>

                                        {/* Appointment Details */}
                                        <div className="flex items center space-x-2 mb-2">
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
                                            {appointment.session_status && (
                                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-50 text-yellow-800 border border-yellow-200">
                                                    Session: {appointment.session_status.replace("_", " ")}
                                                </span>
                                            )}
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-sm text-gray-600">
                                                <span className="font-medium">Start:</span>{" "}
                                                {new Date(appointment.scheduled_start_at).toLocaleString()}
                                            </p>
                                            <p className="text-sm text-gray-600">
                                                <span className="font-medium">End:</span>{" "}
                                                {new Date(appointment.scheduled_end_at).toLocaleString()}
                                            </p>
                                        </div>

                                        {/* Suggested Goals & Targets chips */}
                                        <AppointmentGoalChip appointmentId={String(appointment.id)} />

                                    </div>

                                    {/* Action Buttons */}
                                    <div className="flex flex-col space-y-2 ml-4">
                                        {appointment.status === "scheduled" && (
                                            <Link
                                                href={`/session/${appointment.id}`}
                                                className="inline-flex items-center justify-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                                            >
                                                Join Session
                                            </Link>
                                        )}
                                        {appointment.status === "completed" && (
                                            <Link
                                                href={`/session/${appointment.id}`}
                                                className="inline-flex items-center justify-center px-4 py-2 border border-blue-600 text-sm font-medium rounded-md text-blue-600 bg-white hover:bg-blue-50"
                                            >
                                                View Session History
                                            </Link>
                                        )}
                                    </div>
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
                                                Application #{String(app.id).substring(0, 8)}
                                            </h3>
                                            <span
                                                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${app.status === "submitted"
                                                    ? "bg-yellow-100 text-yellow-800"
                                                    : app.status === "scheduled"
                                                        ? "bg-green-100 text-green-800"
                                                        : "bg-red-100 text-red-800"
                                                    }`}
                                            >
                                                {app.status}
                                            </span>
                                        </div>
                                        <p className="mt-2 text-sm text-gray-600">
                                            <span className="font-medium">Submitted:</span>{" "}
                                            {new Date(fixUtc(app.created_at)).toLocaleDateString()}
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

/** Silently fetch /details and render compact chips for suggested goal & target */
function AppointmentGoalChip({ appointmentId }: { appointmentId: string }) {
    const [details, setDetails] = useState<AppointmentDetailsResponse | null>(null);

    useEffect(() => {
        apiFetch<AppointmentDetailsResponse>(`/api/appointments/${appointmentId}/details`)
            .then(setDetails)
            .catch(() => { /* ignore – user may not have data yet */ });
    }, [appointmentId]);

    if (!details?.goal && !details?.nutrition_target) return null;

    return (
        <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-gray-100">
            {details.goal && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-800 border border-blue-200">
                    🎯 Goal: <span className="capitalize">{details.goal.goal_type}</span>
                    {details.goal.target_delta_kg ? ` · ${details.goal.target_delta_kg}kg` : ""}
                    {details.goal.active ? " (Active)" : " (Suggested)"}
                </span>
            )}
            {details.nutrition_target && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-800 border border-green-200">
                    🥗 Target: {details.nutrition_target.calories_kcal} kcal
                    {details.nutrition_target.active ? " (Active)" : " (Suggested)"}
                </span>
            )}
        </div>
    );
}
