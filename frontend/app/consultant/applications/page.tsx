"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type {
  AppointmentApplicationRead,
  AppointmentRead,
  AppointmentSchedule,
} from "@/lib/types";

export default function ConsultantApplicationsPage() {
  const router = useRouter();

  const [applications, setApplications] = useState<AppointmentApplicationRead[]>(
    []
  );
  const [loading, setLoading] = useState(true);

  const [selectedApp, setSelectedApp] =
    useState<AppointmentApplicationRead | null>(null);
  const [showScheduleModal, setShowScheduleModal] = useState(false);

  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");

  const [scheduling, setScheduling] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // ✅ after accept we store appointment id so we can show “Join Session”
  const [createdAppointmentId, setCreatedAppointmentId] = useState<number | null>(
    null
  );

  // New History State
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [historyApps, setHistoryApps] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [viewingUserId, setViewingUserId] = useState<number | null>(null);

  async function openHistoryModal(userId: number) {
    setViewingUserId(userId);
    setShowHistoryModal(true);
    setHistoryLoading(true);
    setHistoryApps([]);
    try {
      const data = await apiFetch<any[]>(`/api/appointments/users/${userId}/history`);
      setHistoryApps(data);
    } catch (error) {
      console.error("Failed to load history:", error);
    } finally {
      setHistoryLoading(false);
    }
  }

  useEffect(() => {
    loadApplications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadApplications() {
    try {
      const data = await apiFetch<AppointmentApplicationRead[]>(
        "/api/appointments/applications/consultant/me"
      );
      setApplications(data);
    } catch (error) {
      console.error("Failed to load applications:", error);
    } finally {
      setLoading(false);
    }
  }

  const pendingApps = applications.filter((a) => a.status === "submitted");
  const otherApps = applications.filter((a) => a.status !== "submitted");

  function openScheduleModal(app: AppointmentApplicationRead) {
    setSelectedApp(app);
    setShowScheduleModal(true);
    setMessage(null);
    setCreatedAppointmentId(null);

    // Default: tomorrow 10:00 (30 min)
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(10, 0, 0, 0);
    setStartTime(tomorrow.toISOString().slice(0, 16));

    const end = new Date(tomorrow);
    end.setMinutes(end.getMinutes() + 30);
    setEndTime(end.toISOString().slice(0, 16));
  }

  async function handleAccept() {
    if (!selectedApp) return;

    setScheduling(true);
    setMessage(null);

    try {
      const schedule: AppointmentSchedule = {
        scheduled_start_at: new Date(startTime).toISOString(),
        scheduled_end_at: new Date(endTime).toISOString(),
      };

      // ✅ IMPORTANT: capture created appointment
      const created = await apiFetch<AppointmentRead>(
        `/api/appointments/applications/${selectedApp.id}/accept`,
        {
          method: "POST",
          body: schedule,
        }
      );

      setCreatedAppointmentId(created.id);
      setMessage("Application accepted and appointment scheduled!");
      setShowScheduleModal(false);

      await loadApplications();

      // ✅ send consultant straight to chat
      router.push(`/consultant/session/${created.id}`);
    } catch (error: any) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setScheduling(false);
    }
  }

  async function handleReject(appId: number) {
    if (!confirm("Are you sure you want to reject this application?")) return;

    setMessage(null);

    try {
      await apiFetch(`/api/appointments/applications/${appId}/reject`, {
        method: "POST",
      });

      setMessage("Application rejected");
      await loadApplications();
    } catch (error: any) {
      setMessage(`Error: ${error.message}`);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Appointment Applications
        </h1>
        <p className="mt-2 text-sm text-gray-600">
          Review client applications and schedule sessions
        </p>
      </div>

      {message && (
        <div
          className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"
            }`}
        >
          <p
            className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"
              }`}
          >
            {message}
          </p>

          {/* ✅ If we didn’t redirect (or user comes back), show link */}
          {createdAppointmentId && !message.includes("Error") && (
            <div className="mt-2 flex gap-3">
              <Link
                href={`/consultant/session/${createdAppointmentId}`}
                className="text-sm font-medium text-blue-700 underline"
              >
                Join Session Chat
              </Link>
              <Link
                href="/consultant/appointments"
                className="text-sm font-medium text-blue-700 underline"
              >
                View Appointments
              </Link>
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="text-gray-600">Loading applications...</div>
      ) : (
        <>
          <div>
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Pending Applications ({pendingApps.length})
            </h2>

            {pendingApps.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg shadow">
                <p className="text-gray-500">No pending applications</p>
              </div>
            ) : (
              <div className="space-y-4">
                {pendingApps.map((app) => (
                  <div key={app.id} className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-lg font-medium text-gray-900">
                          Application #{app.id}
                        </h3>
                        <p className="text-sm text-gray-600 mt-1">
                          Client User #{app.user_id}
                        </p>
                        {app.note_from_user && (
                          <p className="text-sm text-gray-600 mt-2">
                            <span className="font-medium">Note:</span>{" "}
                            {app.note_from_user}
                          </p>
                        )}
                        <button
                          onClick={() => openHistoryModal(app.user_id)}
                          className="text-sm text-blue-600 hover:text-blue-500 mt-2 underline"
                        >
                          View Applicant History
                        </button>
                      </div>

                      <div className="flex flex-col space-y-2">
                        <button
                          onClick={() => openScheduleModal(app)}
                          className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                        >
                          Accept & Schedule
                        </button>
                        <button
                          onClick={() => handleReject(app.id)}
                          className="px-4 py-2 text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Processed ({otherApps.length})
            </h2>

            {otherApps.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg shadow">
                <p className="text-gray-500">No processed applications</p>
              </div>
            ) : (
              <div className="space-y-3">
                {otherApps.map((app) => (
                  <div key={app.id} className="bg-white rounded-lg shadow p-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          Application #{app.id} • Client #{app.user_id}
                        </p>
                        <p className="text-sm text-gray-600">
                          Status: <span className="capitalize">{app.status}</span>
                        </p>
                        <button
                          onClick={() => openHistoryModal(app.user_id)}
                          className="text-xs text-blue-600 hover:text-blue-500 mt-1 underline"
                        >
                          View Applicant History
                        </button>
                      </div>
                      <Link
                        href="/consultant/appointments"
                        className="text-sm text-blue-600 hover:text-blue-500"
                      >
                        View Appointments →
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {showScheduleModal && selectedApp && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Schedule Appointment
            </h2>
            <p className="text-sm text-gray-600">
              Client #{selectedApp.user_id} • Application #{selectedApp.id}
            </p>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Start Time
                </label>
                <input
                  type="datetime-local"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  End Time
                </label>
                <input
                  type="datetime-local"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowScheduleModal(false)}
                className="px-4 py-2 text-sm font-medium rounded-md text-gray-700 bg-gray-100 hover:bg-gray-200"
                disabled={scheduling}
              >
                Cancel
              </button>
              <button
                onClick={handleAccept}
                className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60"
                disabled={scheduling}
              >
                {scheduling ? "Scheduling..." : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* History Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">
                Applicant History (User #{viewingUserId})
              </h3>
              <button onClick={() => setShowHistoryModal(false)} className="text-gray-500 hover:text-gray-700">✕</button>
            </div>

            {historyLoading ? (
              <p>Loading history...</p>
            ) : historyApps.length === 0 ? (
              <p className="text-gray-500">No past completed sessions found.</p>
            ) : (
              <div className="space-y-3">
                {historyApps.map(appt => (
                  <div key={appt.id} className="border-b pb-2 last:border-0 hover:bg-gray-50 p-2 rounded transition-colors">
                    <Link href={`/consultant/session/${appt.id}`} className="block">
                      <p className="text-sm font-medium text-blue-600 hover:underline">Session #{appt.id}</p>
                      <p className="text-xs text-gray-600">
                        {new Date(appt.scheduled_start_at).toLocaleDateString()}
                      </p>
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 mt-1">
                        Completed
                      </span>
                    </Link>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-4 flex justify-end">
              <button
                onClick={() => setShowHistoryModal(false)}
                className="px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
