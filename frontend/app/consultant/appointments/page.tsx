"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { AppointmentRead, AppointmentDetailsResponse } from "@/lib/types";

function fixDate(d: string): string {
  return d && !d.endsWith("Z") ? d + "Z" : d;
}

function fixAppt(a: AppointmentRead): AppointmentRead {
  return {
    ...a,
    scheduled_start_at: fixDate(a.scheduled_start_at),
    scheduled_end_at: fixDate(a.scheduled_end_at),
    created_at: fixDate(a.created_at),
    updated_at: fixDate(a.updated_at),
  };
}

export default function ConsultantAppointmentsPage() {
  const [appointments, setAppointments] = useState<AppointmentRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    loadAppointments();
  }, []);

  async function loadAppointments() {
    try {
      const raw = await apiFetch<AppointmentRead[]>("/api/appointments/consultant/me");
      setAppointments(raw.map(fixAppt));
    } catch (error: any) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setLoading(false);
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

  const upcomingAppointments = appointments.filter(
    (a) => new Date(a.scheduled_start_at) > new Date() && a.status === "scheduled"
  );

  const pastAppointments = appointments.filter(
    (a) => new Date(a.scheduled_start_at) <= new Date() || a.status !== "scheduled"
  );

  if (loading) {
    return <div className="text-center py-12">Loading appointments...</div>;
  }

  return (
    <div className="space-y-6">
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

      {/* Upcoming Appointments */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Upcoming Appointments ({upcomingAppointments.length})
        </h2>

        {upcomingAppointments.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No upcoming appointments</p>
        ) : (
          <div className="space-y-4">
            {upcomingAppointments.map((appt) => {
              const startDate = new Date(appt.scheduled_start_at);
              const endDate = new Date(appt.scheduled_end_at);
              const duration = Math.round((endDate.getTime() - startDate.getTime()) / 60000);

              return (
                <div key={appt.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      {/* Patient info */}
                      <h3 className="text-lg font-medium text-gray-900">
                        {appt.user_name || `User #${appt.user_id.substring(0, 8)}`}
                      </h3>
                      {appt.user_email && (
                        <p className="text-sm text-gray-500">✉ {appt.user_email}</p>
                      )}
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
                    <Link
                      href={`/consultant/session/${appt.id}`}
                      className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                    >
                      Start Session
                    </Link>
                    <Link
                      href={`/consultant/clients/${appt.user_id}`}
                      className="px-4 py-2 text-sm font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100"
                    >
                      View Client
                    </Link>
                  </div>

                  {/* Suggested Goals & Targets chips */}
                  <AppointmentGoalChip appointmentId={String(appt.id)} />
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Past Appointments */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Past Appointments ({pastAppointments.length})
        </h2>

        {pastAppointments.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No past appointments</p>
        ) : (
          <div className="space-y-4">
            {pastAppointments.map((appt) => {
              const startDate = new Date(appt.scheduled_start_at);
              const endDate = new Date(appt.scheduled_end_at);
              const duration = Math.round((endDate.getTime() - startDate.getTime()) / 60000);

              return (
                <div key={appt.id} className="border border-gray-200 rounded-lg p-4 opacity-85">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      {/* Patient info */}
                      <h3 className="text-lg font-medium text-gray-900">
                        {appt.user_name || `User #${appt.user_id.substring(0, 8)}`}
                      </h3>
                      {appt.user_email && (
                        <p className="text-sm text-gray-500">✉ {appt.user_email}</p>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(appt.status)}`}>
                        {getStatusLabel(appt.status)}
                      </span>
                      {appt.session_status && (
                        <span className="text-xs text-gray-500">
                          Session: {appt.session_status.replace("_", " ")}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="space-y-2 mb-3 text-sm">
                    <div>
                      <span className="font-medium text-gray-700">Date:</span>{" "}
                      {startDate.toLocaleDateString()}
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">Time:</span>{" "}
                      {startDate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} – {endDate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} ({duration} mins)
                    </div>
                  </div>

                  {/* Always show session details link for all past appointments */}
                  <div className="flex gap-4">
                    <Link
                      href={`/consultant/session/${appt.id}`}
                      className="text-sm font-medium text-blue-600 hover:text-blue-700"
                    >
                      View / Manage Session →
                    </Link>
                    <Link
                      href={`/consultant/clients/${appt.user_id}`}
                      className="text-sm font-medium text-blue-600 hover:text-blue-700"
                    >
                      View Client →
                    </Link>
                  </div>

                  {/* Suggested Goals & Targets chips */}
                  <AppointmentGoalChip appointmentId={String(appt.id)} />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

/** Silently fetch /details and render compact chips for suggested goal & target */
function AppointmentGoalChip({ appointmentId }: { appointmentId: string }) {
  const [details, setDetails] = useState<AppointmentDetailsResponse | null>(null);

  useEffect(() => {
    apiFetch<AppointmentDetailsResponse>(`/api/appointments/${appointmentId}/details`)
      .then(setDetails)
      .catch(() => { /* ignore – consultant or data may not exist yet */ });
  }, [appointmentId]);

  if (!details?.goal && !details?.nutrition_target) return null;

  return (
    <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-gray-100">
      {details.goal && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-800 border border-blue-200">
          🎯 Goal: <span className="capitalize">{details.goal.goal_type}</span>
          {details.goal.target_weight ? ` · Target Weight: ${details.goal.target_weight}kg` : ""}
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
