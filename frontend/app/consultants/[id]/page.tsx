"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { ConsultantPublicRead, ConsultationRequestRead } from "@/lib/types";

export default function ConsultantDetailPage() {
    const params = useParams();
    const router = useRouter();
    const consultantId = params.id as string;

    const [consultant, setConsultant] = useState<ConsultantPublicRead | null>(null);
    const [loading, setLoading] = useState(true);
    const [issue, setIssue] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    useEffect(() => {
        async function loadConsultant() {
            if (!consultantId) return;
            try {
                const data = await apiFetch<ConsultantPublicRead>(`/api/consultants/${consultantId}`);
                setConsultant(data);
            } catch (error: any) {
                setMessage(`Error loading consultant: ${error.message}`);
            } finally {
                setLoading(false);
            }
        }
        loadConsultant();
    }, [consultantId]);

    async function handleRequest() {
        if (!consultant || !issue.trim()) return;

        setSubmitting(true);
        setMessage(null);

        try {
            await apiFetch<ConsultationRequestRead>("/api/consultations/requests", {
                method: "POST",
                body: {
                    consultant_user_id: consultant.user_id,
                    issue: issue.trim(),
                },
            });

            setMessage("Request sent! You'll be able to chat once the consultant replies.");
            setTimeout(() => {
                router.push("/consultations");
            }, 1200);
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setSubmitting(false);
        }
    }

    if (loading) {
        return <div className="text-center py-12">Loading consultant profile...</div>;
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
        <div className="max-w-5xl mx-auto p-6 space-y-6">
            <Link href="/consultants" className="text-sm text-blue-600 hover:text-blue-500">
                ← Back to consultants
            </Link>

            {message && (
                <div className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                    <p className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                        {message}
                    </p>
                </div>
            )}

            {/* Profile */}
            <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-start justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">{consultant.display_name}</h1>
                        {consultant.is_verified && (
                            <span className="inline-block mt-2 px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                                ✓ Verified
                            </span>
                        )}
                    </div>
                </div>

                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <p className="text-sm font-medium text-gray-700">Type</p>
                        <p className="mt-1 text-gray-900 capitalize">{consultant.consultant_type.replace("_", " ")}</p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-gray-700">Qualification</p>
                        <p className="mt-1 text-gray-900">{consultant.highest_qualification}</p>
                    </div>
                    {consultant.graduation_institution && (
                        <div>
                            <p className="text-sm font-medium text-gray-700">Institution</p>
                            <p className="mt-1 text-gray-900">{consultant.graduation_institution}</p>
                        </div>
                    )}
                    {consultant.specialties && (
                        <div>
                            <p className="text-sm font-medium text-gray-700">Specialties</p>
                            <p className="mt-1 text-gray-900">{consultant.specialties}</p>
                        </div>
                    )}
                </div>

                {consultant.bio && (
                    <div className="mt-4">
                        <p className="text-sm font-medium text-gray-700">About</p>
                        <p className="mt-1 text-gray-900 whitespace-pre-line">{consultant.bio}</p>
                    </div>
                )}
            </div>

            {/* Request a consultation */}
            <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-1">Request a Consultation</h2>
                <p className="text-sm text-gray-500 mb-4">
                    Describe your issue and send a request. Once the consultant replies, a chat opens
                    where you can agree on a time for your consultation.
                </p>

                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        What would you like help with?
                    </label>
                    <textarea
                        rows={4}
                        className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 px-3 py-2 border"
                        placeholder="e.g. I'd like guidance on a weight-loss plan and managing my diet..."
                        value={issue}
                        onChange={(e) => setIssue(e.target.value)}
                    />
                </div>

                <button
                    onClick={handleRequest}
                    disabled={!issue.trim() || submitting}
                    className="w-full md:w-auto px-6 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                    {submitting ? "Sending..." : "Send Request"}
                </button>
            </div>
        </div>
    );
}
