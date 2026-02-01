"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type {
  AppointmentApplicationRead,
  AppointmentRead,
  AppointmentSchedule,
  ProposeTimeRequest,
} from "@/lib/types";

export default function ConsultantApplicationsPage() {
  const router = useRouter();

  const [applications, setApplications] = useState<AppointmentApplicationRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  // Modal states
  const [selectedApp, setSelectedApp] = useState<AppointmentApplicationRead | null>(null);
  const [showProposeModal, setShowProposeModal] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);

  const [proposedTime, setProposedTime] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");

  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadApplications();
  }, []);

  function fixDate(d: string): string;
  function fixDate(d: string | null | undefined): string | null;
  function fixDate(d: string | null | undefined): string | null {
    if (d === undefined || d === null) return null;
    return d.endsWith("Z") ? d : d + "Z";
  }

  async function loadApplications() {
    try {
      const raw = await apiFetch<AppointmentApplicationRead[]>(
        "/api/appointments/applications/consultant/me"
      );
      const data = raw.map((app) => ({
        ...app,
        requested_start_at: fixDate(app.requested_start_at),
        proposed_start_at: fixDate(app.proposed_start_at),
        proposed_at: fixDate(app.proposed_at),
        proposal_accepted_at: fixDate(app.proposal_accepted_at),
        created_at: fixDate(app.created_at),
        updated_at: fixDate(app.updated_at),
      }));
      setApplications(data);
    } catch (error: any) {
      console.error("Failed to load applications:", error);
      setMessage(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  const submittedApps = applications.filter((a) => a.status === "submitted");
  const proposedApps = applications.filter((a) => a.status === "proposed");
  const acceptedApps = applications.filter((a) => a.status === "proposal_accepted");
  const scheduledApps = applications.filter((a) => a.status === "scheduled");

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

  function toLocalISOString(date: Date): string {
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }

  function openProposeModal(app: AppointmentApplicationRead) {
    setSelectedApp(app);
    setShowProposeModal(true);
    setMessage(null);

    // Default to tomorrow at the requested time
    const tomorrow = new Date(app.requested_start_at);
    tomorrow.setDate(tomorrow.getDate() + 1);
    setProposedTime(toLocalISOString(tomorrow));
  }

  async function handlePropose() {
    if (!selectedApp || !proposedTime) return;

    setSubmitting(true);
    setMessage(null);

    try {
      const payload: ProposeTimeRequest = {
        proposed_start_at: new Date(proposedTime).toISOString(),
      };

      await apiFetch(`/api/appointments/applications/${selectedApp.id}/propose`, {
        method: "POST",
        body: payload,
      });

      setMessage("Proposal sent to user");
      setShowProposeModal(false);
      await loadApplications();
    } catch (error: any) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  function openScheduleModal(app: AppointmentApplicationRead) {
    setSelectedApp(app);
    setShowScheduleModal(true);
    setMessage(null);

    // Set start time based on application status
    const startDate =
      app.status === "proposal_accepted" && app.proposed_start_at
        ? new Date(app.proposed_start_at)
        : new Date(app.requested_start_at);

    setStartTime(toLocalISOString(startDate));

    // Default end time: 30 minutes later
    const endDate = new Date(startDate);
    endDate.setMinutes(endDate.getMinutes() + 30);
    setEndTime(toLocalISOString(endDate));
  }

  async function handleSchedule() {
    if (!selectedApp || !endTime) return;

    setSubmitting(true);
    setMessage(null);

    try {
      const schedule: AppointmentSchedule = {
        scheduled_start_at: new Date(startTime).toISOString(),
        scheduled_end_at: new Date(endTime).toISOString(),
      };

      const created = await apiFetch<AppointmentRead>(
        `/api/appointments/applications/${selectedApp.id}/schedule`,
        {
          method: "POST",
          body: schedule,
        }
      );

      setMessage("Appointment scheduled successfully!");
      setShowScheduleModal(false);

      await loadApplications();

      // Redirect to session
      router.push(`/consultant/session/${created.id}`);
    } catch (error: any) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <div className="text-center py-12">Loading applications...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Appointment Applications</h1>
        <p className="mt-2 text-sm text-gray-600">
          Review and manage incoming appointment requests
        </p>
      </div>

      {message && (
        <div className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
          <p className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}>
            {message}
          </p>
        </div>
      )}

      {/* Tab View */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <div className="px-6 py-3 text-sm font-medium border-b-2 border-blue-500 text-blue-600">
              New Requests ({submittedApps.length})
            </div>
          </nav>
        </div>

        <div className="p-6">
          {submittedApps.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No new requests</p>
          ) : (
            <div className="space-y-4">
              {submittedApps.map((app) => (
                <div key={app.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="text-lg font-medium text-gray-900">
                        Application #{app.id}
                      </h3>
                      <p className="text-sm text-gray-600">
                        User #{app.user_id}
                      </p>
                    </div>
                  </div>

                  <div className="space-y-2 mb-4 text-sm">
                    <div>
                      <span className="font-medium text-gray-700">Requested Time:</span>{" "}
                      {new Date(app.requested_start_at).toLocaleString()}
                    </div>
                    {app.note_from_user && (
                      <div>
                        <span className="font-medium text-gray-700">Note:</span>
                        <p className="text-gray-600 italic mt-1">"{app.note_from_user}"</p>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => openScheduleModal(app)}
                      className="px-4 py-2 text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
                    >
                      Accept & Schedule
                    </button>
                    <button
                      onClick={() => openProposeModal(app)}
                      className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                    >
                      Propose Time
                    </button>
                    <button
                      onClick={() => handleReject(app.id)}
                      className="px-4 py-2 text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Waiting for User Tab */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <div className="px-6 py-3 text-sm font-medium text-gray-700">
            Waiting for User ({proposedApps.length})
          </div>
        </div>

        <div className="p-6">
          {proposedApps.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No pending proposals</p>
          ) : (
            <div className="space-y-4">
              {proposedApps.map((app) => (
                <div key={app.id} className="border border-gray-200 rounded-lg p-4">
                  <h3 className="font-medium text-gray-900">Application #{app.id}</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Proposed: {new Date(app.proposed_start_at!).toLocaleString()}
                  </p>
                  <p className="text-sm text-gray-500 mt-2">Waiting for user to accept...</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Ready to Schedule Tab */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <div className="px-6 py-3 text-sm font-medium text-gray-700">
            Ready to Schedule ({acceptedApps.length})
          </div>
        </div>

        <div className="p-6">
          {acceptedApps.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No accepted proposals</p>
          ) : (
            <div className="space-y-4">
              {acceptedApps.map((app) => (
                <div key={app.id} className="border border-gray-200 rounded-lg p-4">
                  <h3 className="font-medium text-gray-900">Application #{app.id}</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Accepted Time: {new Date(app.proposed_start_at!).toLocaleString()}
                  </p>
                  <button
                    onClick={() => openScheduleModal(app)}
                    className="mt-3 px-4 py-2 text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
                  >
                    Schedule Appointment
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Propose Modal */}
      {showProposeModal && selectedApp && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Propose Alternative Time
            </h2>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Proposed Start Time
              </label>
              <input
                type="datetime-local"
                value={proposedTime}
                onChange={(e) => setProposedTime(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowProposeModal(false)}
                disabled={submitting}
                className="px-4 py-2 text-sm font-medium rounded-md text-gray-700 bg-gray-100 hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handlePropose}
                disabled={submitting}
                className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60"
              >
                {submitting ? "Sending..." : "Send Proposal"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Schedule Modal */}
      {showScheduleModal && selectedApp && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Schedule Appointment
            </h2>

            <div className="space-y-3 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Start Time (determined by application)
                </label>
                <input
                  type="datetime-local"
                  value={startTime}
                  disabled
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  End Time
                </label>
                <input
                  type="datetime-local"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowScheduleModal(false)}
                disabled={submitting}
                className="px-4 py-2 text-sm font-medium rounded-md text-gray-700 bg-gray-100 hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleSchedule}
                disabled={submitting}
                className="px-4 py-2 text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-60"
              >
                {submitting ? "Scheduling..." : "Confirm Schedule"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
