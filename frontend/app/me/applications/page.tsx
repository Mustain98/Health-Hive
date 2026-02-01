"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { AppointmentApplicationRead } from "@/lib/types";

export default function MyApplicationsPage() {
    const [applications, setApplications] = useState<AppointmentApplicationRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [message, setMessage] = useState<string | null>(null);

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
            const raw = await apiFetch<AppointmentApplicationRead[]>("/api/appointments/applications/me");
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
            setMessage(`Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    }

    async function handleAcceptProposal(applicationId: number) {
        setMessage(null);
        try {
            await apiFetch(`/api/appointments/applications/${applicationId}/accept-proposal`, {
                method: "POST",
            });
            setMessage("Proposal accepted! Waiting for consultant to schedule.");
            await loadApplications();
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        }
    }

    async function handleCancel(applicationId: number) {
        if (!confirm("Are you sure you want to cancel this application?")) return;

        setMessage(null);
        try {
            await apiFetch(`/api/appointments/applications/${applicationId}/cancel`, {
                method: "POST",
            });
            setMessage("Application cancelled successfully");
            await loadApplications();
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        }
    }

    function getStatusColor(status: string): string {
        switch (status) {
            case "submitted":
                return "bg-yellow-100 text-yellow-800";
            case "proposed":
                return "bg-blue-100 text-blue-800";
            case "proposal_accepted":
                return "bg-purple-100 text-purple-800";
            case "scheduled":
                return "bg-green-100 text-green-800";
            case "rejected":
                return "bg-red-100 text-red-800";
            case "cancelled":
                return "bg-gray-100 text-gray-800";
            default:
                return "bg-gray-100 text-gray-800";
        }
    }

    function getStatusLabel(status: string): string {
        return status.replace("_", " ").split(" ").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
    }

    if (loading) {
        return <div className="text-center py-12">Loading applications...</div>;
    }

    return (
        <div className="max-w-4xl mx-auto p-6 space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">My Applications</h1>
                <p className="mt-2 text-sm text-gray-600">
                    Track your appointment applications and respond to consultant proposals
                </p>
            </div>

            {message && (
                <div className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                    <p className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                        {message}
                    </p>
                </div>
            )}

            {applications.length === 0 ? (
                <div className="bg-white rounded-lg shadow p-12 text-center">
                    <p className="text-gray-500 mb-4">No applications yet</p>
                    <Link
                        href="/consultants"
                        className="inline-block px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                    >
                        Browse Consultants
                    </Link>
                </div>
            ) : (
                <div className="space-y-4">
                    {applications.map((app) => (
                        <div key={app.id} className="bg-white rounded-lg shadow p-6">
                            <div className="flex items-start justify-between mb-4">
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-900">
                                        Application #{app.id}
                                    </h3>
                                    <p className="text-sm text-gray-600">
                                        Consultant User #{app.consultant_user_id}
                                    </p>
                                </div>
                                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(app.status)}`}>
                                    {getStatusLabel(app.status)}
                                </span>
                            </div>

                            {/* Timeline */}
                            <div className="space-y-2 mb-4 text-sm">
                                <div>
                                    <span className="font-medium text-gray-700">Requested Time:</span>{" "}
                                    <span className="text-gray-900">
                                        {new Date(app.requested_start_at).toLocaleString()}
                                    </span>
                                </div>

                                {app.proposed_start_at && (
                                    <div>
                                        <span className="font-medium text-gray-700">Consultant Proposed:</span>{" "}
                                        <span className="text-gray-900">
                                            {new Date(app.proposed_start_at).toLocaleString()}
                                        </span>
                                        {app.proposed_at && (
                                            <span className="text-gray-500 ml-2">
                                                (on {new Date(app.proposed_at).toLocaleDateString()})
                                            </span>
                                        )}
                                    </div>
                                )}

                                {app.proposal_accepted_at && (
                                    <div>
                                        <span className="font-medium text-gray-700">Accepted On:</span>{" "}
                                        <span className="text-gray-900">
                                            {new Date(app.proposal_accepted_at).toLocaleDateString()}
                                        </span>
                                    </div>
                                )}
                            </div>

                            {app.note_from_user && (
                                <div className="mb-4 text-sm">
                                    <span className="font-medium text-gray-700">Your Message:</span>
                                    <p className="text-gray-600 mt-1 italic">"{app.note_from_user}"</p>
                                </div>
                            )}

                            {/* Actions */}
                            <div className="flex gap-3 pt-3 border-t border-gray-200">
                                {app.status === "submitted" && (
                                    <>
                                        <p className="text-sm text-gray-600 flex-1">Waiting for consultant response...</p>
                                        <button
                                            onClick={() => handleCancel(app.id)}
                                            className="px-4 py-2 text-sm font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200"
                                        >
                                            Cancel
                                        </button>
                                    </>
                                )}

                                {app.status === "proposed" && (
                                    <>
                                        <button
                                            onClick={() => handleAcceptProposal(app.id)}
                                            className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                                        >
                                            Accept Proposed Time
                                        </button>
                                        <button
                                            onClick={() => handleCancel(app.id)}
                                            className="px-4 py-2 text-sm font-medium rounded-md text-gray-700 bg-gray-100 hover:bg-gray-200"
                                        >
                                            Cancel
                                        </button>
                                    </>
                                )}

                                {app.status === "proposal_accepted" && (
                                    <p className="text-sm text-gray-600">Waiting for consultant to finalize schedule...</p>
                                )}

                                {app.status === "scheduled" && (
                                    <Link
                                        href="/me/appointments"
                                        className="text-sm font-medium text-blue-600 hover:text-blue-700"
                                    >
                                        View Appointments →
                                    </Link>
                                )}

                                {app.status === "rejected" && (
                                    <p className="text-sm text-red-600">This application was rejected by the consultant</p>
                                )}

                                {app.status === "cancelled" && (
                                    <p className="text-sm text-gray-600">This application was cancelled</p>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
