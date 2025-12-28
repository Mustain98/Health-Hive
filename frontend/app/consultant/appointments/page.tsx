"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { AppointmentRead } from "@/lib/types";

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
  const [appointments, setAppointments] = useState<AppointmentRead[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAppointments() {
      try {
        const data = await apiFetch<AppointmentRead[]>(
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

  const now = useMemo(() => new Date(), []);

  const { active, past } = useMemo(() => {
    const current = new Date();
    const activeList: AppointmentRead[] = [];
    const pastList: AppointmentRead[] = [];

    for (const a of appointments) {
      const state = getSessionState(a, current);

      // “Active tab” contains: upcoming + active (joinable)
      if (state.canJoin && a.status === "scheduled") activeList.push(a);
      else pastList.push(a);
    }

    // sort: upcoming first then active
    activeList.sort(
      (a, b) =>
        new Date(a.scheduled_start_at).getTime() - new Date(b.scheduled_start_at).getTime()
    );

    // sort: most recent first
    pastList.sort(
      (a, b) =>
        new Date(b.scheduled_start_at).getTime() - new Date(a.scheduled_start_at).getTime()
    );

    return { active: activeList, past: pastList };
  }, [appointments]);

  if (loading) {
    return <div className="text-center py-12 text-gray-600">Loading appointments...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Appointments / Sessions</h1>
        <p className="mt-2 text-sm text-gray-600">
          Join sessions, chat with clients, and manage client data when permitted.
        </p>
      </div>

      {/* Active / Upcoming */}
      <div>
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Active / Upcoming ({active.length})
        </h2>

        {active.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-500">No active or upcoming appointments.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {active.map((appointment) => {
              const state = getSessionState(appointment, new Date());
              return (
                <div key={appointment.id} className="bg-white shadow rounded-lg p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-medium text-gray-900">
                          Appointment #{appointment.id}
                        </h3>
                        <Badge label={state.label} kind={state.kind} />
                      </div>
                      <p className="text-sm text-gray-600 mt-1">
                        Client User #{appointment.user_id}
                      </p>

                      <div className="mt-3 space-y-1">
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">Start:</span>{" "}
                          {new Date(appointment.scheduled_start_at).toLocaleString()}
                        </p>
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">End:</span>{" "}
                          {new Date(appointment.scheduled_end_at).toLocaleString()}
                        </p>
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">Status:</span>{" "}
                          <span className="capitalize">{appointment.status}</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-col gap-2 min-w-[170px]">
                      {/* ✅ Join session (enabled for upcoming/active) */}
                      <Link
                        href={`/consultant/session/${appointment.id}`}
                        className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                      >
                        Join Session
                      </Link>

                      {/* ✅ Client management */}
                      <Link
                        href={`/consultant/clients/${appointment.user_id}`}
                        className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
                      >
                        View Client
                      </Link>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Past */}
      <div>
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Past / Ended ({past.length})
        </h2>

        {past.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-500">No past appointments yet.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {past.map((appointment) => {
              const state = getSessionState(appointment, new Date());
              return (
                <div key={appointment.id} className="bg-white shadow rounded-lg p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-gray-900">
                          Appointment #{appointment.id} • Client #{appointment.user_id}
                        </p>
                        <Badge label={state.label} kind={state.kind} />
                      </div>
                      <p className="text-sm text-gray-600">
                        {new Date(appointment.scheduled_start_at).toLocaleString()} –{" "}
                        {new Date(appointment.scheduled_end_at).toLocaleString()}
                      </p>
                      <p className="text-sm text-gray-600">
                        Status: <span className="capitalize">{appointment.status}</span>
                      </p>
                    </div>

                    <div className="flex items-center gap-3">
                      {/* ✅ If ended/cancelled/completed: open chat/history */}
                      {state.canOpen && (
                        <Link
                          href={`/consultant/session/${appointment.id}`}
                          className="text-sm font-medium text-blue-600 hover:text-blue-500"
                        >
                          Open Chat →
                        </Link>
                      )}

                      <Link
                        href={`/consultant/clients/${appointment.user_id}`}
                        className="text-sm font-medium text-blue-600 hover:text-blue-500"
                      >
                        View Client →
                      </Link>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
