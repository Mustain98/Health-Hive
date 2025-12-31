"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { ConsultantPublicRead, ConsultantDocumentRead, AppointmentApplicationCreate } from "@/lib/types";

export default function ConsultantDetailPage() {
    const params = useParams();
    const router = useRouter();
    const consultantId = params.id as string;

    const [consultant, setConsultant] = useState<ConsultantPublicRead | null>(null);
    const [documents, setDocuments] = useState<ConsultantDocumentRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [showApplyModal, setShowApplyModal] = useState(false);
    const [note, setNote] = useState("");
    const [applying, setApplying] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    useEffect(() => {
        async function loadConsultant() {
            try {
                const [consultantData, docsData] = await Promise.all([
                    apiFetch<ConsultantPublicRead>(`/api/consultants/${consultantId}`),
                    apiFetch<ConsultantDocumentRead[]>(`/api/consultants/${consultantId}/documents`).catch(() => []),
                ]);

                setConsultant(consultantData);
                setDocuments(docsData);
            } catch (error: any) {
                setMessage(`Error loading consultant: ${error.message}`);
            } finally {
                setLoading(false);
            }
        }
        loadConsultant();
    }, [consultantId]);

    async function handleApply() {
        if (!consultant) return;

        setApplying(true);
        setMessage(null);

        try {
            const application: AppointmentApplicationCreate = {
                consultant_user_id: consultant.user_id,
                note_from_user: note || null,
            };

            await apiFetch("/api/appointments/applications", {
                method: "POST",
                body: application,
            });

            setMessage("Application submitted successfully!");
            setShowApplyModal(false);
            setNote("");

            // Redirect to appointments after a delay
            setTimeout(() => {
                router.push("/appointments");
            }, 2000);
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setApplying(false);
        }
    }

    if (loading) {
        return <div className="text-center py-12">Loading...</div>;
    }

    if (!consultant) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500">Consultant not found</p>
                <Link href="/consultants" className="text-blue-600 hover:text-blue-500 mt-4 inline-block">
                    ← Back to consultants
                </Link>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <Link href="/consultants" className="text-sm text-blue-600 hover:text-blue-500">
                    ← Back to consultants
                </Link>
            </div>

            {message && (
                <div className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                    <p className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                        {message}
                    </p>
                </div>
            )}

            {/* Profile Header */}
            <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-start justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">{consultant.display_name}</h1>
                        {consultant.is_verified && (
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 mt-2">
                                ✓ Verified Consultant
                            </span>
                        )}
                    </div>
                    <button
                        onClick={() => setShowApplyModal(true)}
                        className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                    >
                        Apply for Appointment
                    </button>
                </div>

                {consultant.specialties && (
                    <div className="mt-4">
                        <h3 className="text-sm font-medium text-gray-700">Specialties</h3>
                        <p className="mt-1 text-gray-900">{consultant.specialties}</p>
                    </div>
                )}

                {consultant.bio && (
                    <div className="mt-4">
                        <h3 className="text-sm font-medium text-gray-700">About</h3>
                        <p className="mt-1 text-gray-900 whitespace-pre-line">{consultant.bio}</p>
                    </div>
                )}
            </div>

            {/* Certificates */}
            {documents.length > 0 && (
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Certificates & Documents</h2>
                    <div className="space-y-4">
                        {documents.map((doc) => (
                            <div key={doc.id} className="border border-gray-200 rounded-lg p-4">
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <h3 className="text-sm font-medium text-gray-900">{doc.title}</h3>
                                        {doc.issuer && (
                                            <p className="text-sm text-gray-600 mt-1">Issued by: {doc.issuer}</p>
                                        )}
                                        {doc.issue_date && (
                                            <p className="text-sm text-gray-600 mt-1">
                                                Date: {new Date(doc.issue_date).toLocaleDateString()}
                                            </p>
                                        )}
                                    </div>
                                    {doc.file_url && (
                                        <a
                                            href={doc.file_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-sm text-blue-600 hover:text-blue-500"
                                        >
                                            View →
                                        </a>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Apply Modal */}
            {showApplyModal && (
                <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">
                            Apply for Appointment with {consultant.display_name}
                        </h3>

                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Message (Optional)
                            </label>
                            <textarea
                                rows={4}
                                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                placeholder="Tell the consultant why you'd like to book an appointment..."
                                value={note}
                                onChange={(e) => setNote(e.target.value)}
                            />
                        </div>

                        <div className="flex justify-end space-x-3">
                            <button
                                onClick={() => setShowApplyModal(false)}
                                disabled={applying}
                                className="px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleApply}
                                disabled={applying}
                                className="px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                            >
                                {applying ? "Submitting..." : "Submit Application"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
