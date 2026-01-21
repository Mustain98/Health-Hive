"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { AppointmentRead, AppointmentReadWithUser } from "@/lib/types";

function Badge({ label, kind }: { label: string; kind: "green" | "blue" | "gray" | "red" }) {
  const cls =
    kind === "green"
      ? "bg-green-50 text-green-700 border-green-200"
      : kind === "blue"
        ? "bg-blue-50 text-blue-700 border-blue-200"
        : kind === "red"
          ? "bg-red-50 text-red-700 border-red-200"
          : "bg-gray-50 text-gray-700 border-gray-200";

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}

function getSessionState(a: AppointmentRead, now: Date) {
  const start = new Date(a.scheduled_start_at).getTime();
  const end = new Date(a.scheduled_end_at).getTime();
  const t = now.getTime();

  // If backend marks status, honor it first
  if (a.status === "cancelled") return { label: "Cancelled", kind: "red" as const, canJoin: false, canOpen: true };
  if (a.status === "no_show") return { label: "No Show", kind: "gray" as const, canJoin: false, canOpen: true };
  if (a.status === "completed") return { label: "Completed", kind: "gray" as const, canJoin: false, canOpen: true };

  // Scheduled
  if (t < start) return { label: "Upcoming", kind: "blue" as const, canJoin: true, canOpen: true };
  if (t >= start && t <= end) return { label: "Session Active", kind: "green" as const, canJoin: true, canOpen: true };
  return { label: "Ended", kind: "gray" as const, canJoin: false, canOpen: true };
}

export default function ConsultantAppointmentsPage() {
  const [appointments, setAppointments] = useState<AppointmentReadWithUser[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAppointments() {
      try {
        const data = await apiFetch<AppointmentReadWithUser[]>(
          "/api/appointments/consultant/me"
        );
        setAppointments(data);
      } catch (error) {
        console.error("Failed to load appointments:", error);
      } finally {
        setLoading(false);
      }
    }
    loadAppointments();
  }, []);

  const { ongoing, upcoming, past } = useMemo(() => {
    const ongoingList: AppointmentReadWithUser[] = [];
    const upcomingList: AppointmentReadWithUser[] = [];
    const pastList: AppointmentReadWithUser[] = [];

    for (const a of appointments) {
      // 1. Ongoing: Session is explicitly ACTIVE
      if (a.session_status === 'active') {
        ongoingList.push(a);
        continue;
      }

      // 2. Past: Ended status or Appointment completed/cancelled
      if (a.session_status === 'ended' || ['completed', 'cancelled', 'no_show'].includes(a.status)) {
        pastList.push(a);
        continue;
      }

      // 3. Upcoming: Scheduled and not started
      if (a.status === 'scheduled') {
        upcomingList.push(a);
        continue;
      }

      // Fallback (shouldn't happen often) -> Past
      pastList.push(a);
    }

    // Sort: All lists sorted by scheduled start time
    // Ongoing: urgent first? or standard time order? standard time.
    ongoingList.sort((a, b) => new Date(a.scheduled_start_at).getTime() - new Date(b.scheduled_start_at).getTime());
    upcomingList.sort((a, b) => new Date(a.scheduled_start_at).getTime() - new Date(b.scheduled_start_at).getTime());
    pastList.sort((a, b) => new Date(b.scheduled_start_at).getTime() - new Date(a.scheduled_start_at).getTime());

    return { ongoing: ongoingList, upcoming: upcomingList, past: pastList };
  }, [appointments]);

  if (loading) return <div className="text-center py-12 text-gray-600">Loading appointments...</div>;

  const renderCard = (appointment: AppointmentReadWithUser, isPast: boolean) => {
    const state = getSessionState(appointment, new Date());
    // Override label for clarity if needed, but existing logic is decent.

    return (
      <div key={appointment.id} className={`bg-white shadow rounded-lg p-6 ${isPast ? 'opacity-80 hover:opacity-100 transition-opacity' : ''}`}>
        <div className="flex flex-col md:flex-row items-start justify-between gap-6">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-lg font-semibold text-gray-900">
                {appointment.user.full_name || appointment.user.username}
              </h3>
              <Badge label={state.label} kind={state.kind} />
            </div>
            <div className="text-sm text-gray-500 space-y-1">
              <p className="flex items-center gap-2">
                <span className="font-medium text-gray-700">Client Email:</span> {appointment.user.email}
              </p>
              <p className="flex items-center gap-2">
                <span className="font-medium text-gray-700">Time:</span>
                {new Date(appointment.scheduled_start_at).toLocaleString()} – {new Date(appointment.scheduled_end_at).toLocaleTimeString()}
              </p>
              {appointment.user_data && (
                <div className="mt-2 p-2 bg-gray-50 rounded text-xs text-gray-700 grid grid-cols-2 gap-x-4 gap-y-1">
                  <p><strong>Age:</strong> {appointment.user_data.age ?? 'N/A'}</p>
                  <p><strong>Gender:</strong> <span className="capitalize">{appointment.user_data.gender ?? 'N/A'}</span></p>
                  <p><strong>Height:</strong> {appointment.user_data.height_cm ? `${appointment.user_data.height_cm} cm` : 'N/A'}</p>
                  <p><strong>Weight:</strong> {appointment.user_data.weight_kg ? `${appointment.user_data.weight_kg} kg` : 'N/A'}</p>
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
            {!isPast ? (
              <>
                <Link
                  href={`/consultant/session/${appointment.id}`}
                  className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 w-full sm:w-auto"
                >
                  Open Session
                </Link>
                <Link
                  href={`/consultant/clients/${appointment.user_id}`}
                  className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 w-full sm:w-auto"
                >
                  Client Profile
                </Link>
              </>
            ) : (
              <>
                {state.canOpen && (
                  <Link
                    href={`/consultant/session/${appointment.id}`}
                    className="text-sm font-medium text-blue-600 hover:text-blue-500"
                  >
                    View Session
                  </Link>
                )}
                <Link
                  href={`/consultant/clients/${appointment.user_id}`}
                  className="text-sm font-medium text-gray-600 hover:text-gray-500"
                >
                  Profile
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Appointments / Sessions</h1>
        <p className="mt-2 text-sm text-gray-600">
          Join sessions, chat with clients, and manage client data when permitted.
        </p>
      </div>

      {ongoing.length > 0 && (
        <div>
          <h2 className="text-xl font-bold text-green-700 mb-4 flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-green-600 animate-pulse"></span>
            Ongoing Sessions ({ongoing.length})
          </h2>
          <div className="space-y-4">
            {ongoing.map(a => renderCard(a, false))}
          </div>
        </div>
      )}

      <div>
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Upcoming ({upcoming.length})
        </h2>
        {upcoming.length === 0 && ongoing.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 rounded-lg"><p className="text-gray-500">No active or upcoming appointments.</p></div>
        ) : (
          <div className="space-y-4">
            {upcoming.map(a => renderCard(a, false))}
          </div>
        )}
      </div>

      <div>
        <h2 className="text-lg font-medium text-gray-900 mb-4">Past / Ended ({past.length})</h2>
        {past.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 rounded-lg"><p className="text-gray-500">No past appointments.</p></div>
        ) : (
          <div className="space-y-4">
            {past.map(a => renderCard(a, true))}
          </div>
        )}
      </div>
    </div>
  );
}
