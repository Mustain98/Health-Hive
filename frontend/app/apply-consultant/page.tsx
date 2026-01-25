"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch, apiUpload } from "@/lib/api";
import { useAuth } from "@/components/guards/AuthGuard";
import type { ConsultantProfileCreate, ConsultantProfileRead, ConsultantDocumentRead } from "@/lib/types";

export default function ApplyConsultantPage() {
    const router = useRouter();
    const { user } = useAuth();

    const [form, setForm] = useState<ConsultantProfileCreate>({
        display_name: "",
        bio: "",
        specialties: "",
        other_info: "",
        consultant_type: "clinical",
        highest_qualification: "",
        graduation_institution: "",
        registration_body: "",
        registration_number: "",
    });

    const [documents, setDocuments] = useState<File[]>([]);
    const [uploading, setUploading] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        setUploading(true);
        setMessage(null);

        try {
            // Create consultant profile
            const profile = await apiFetch<ConsultantProfileRead>("/api/consultants/me/profile", {
                method: "PUT",
                body: form,
            });

            // Upload documents if any
            if (documents.length > 0) {
                for (const doc of documents) {
                    const formData = new FormData();
                    formData.append("file", doc);
                    formData.append("consultant_profile_id", profile.id.toString());
                    formData.append("title", doc.name.replace(/\.[^/.]+$/, "")); // Remove extension
                    formData.append("doc_type", "certificate");

                    await apiUpload<ConsultantDocumentRead>("/api/consultants/me/documents", formData);
                }
            }

            setMessage("Application submitted successfully! Your profile will be reviewed by our team.");

            // Redirect to dashboard after 3 seconds
            setTimeout(() => {
                router.push("/dashboard");
            }, 3000);
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setUploading(false);
        }
    }

    function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
        if (e.target.files) {
            setDocuments(Array.from(e.target.files));
        }
    }

    // Redirect if not logged in
    if (!user) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
                <div className="max-w-md w-full text-center">
                    <h2 className="text-2xl font-bold text-gray-900 mb-4">Login Required</h2>
                    <p className="text-gray-600 mb-6">
                        You must be logged in to apply as a consultant.
                    </p>
                    <Link
                        href="/login"
                        className="inline-block px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                    >
                        Login
                    </Link>
                </div>
            </div>
        );
    }

    // Check if already consultant
    if (user.user_type === "consultant") {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
                <div className="max-w-md w-full text-center">
                    <h2 className="text-2xl font-bold text-gray-900 mb-4">Already a Consultant</h2>
                    <p className="text-gray-600 mb-6">
                        You are already registered as a consultant.
                    </p>
                    <Link
                        href="/consultant/profile"
                        className="inline-block px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                    >
                        Go to Consultant Profile
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-gray-900">Apply as a Consultant</h1>
                    <p className="mt-2 text-sm text-gray-600">
                        Join our network of expert health consultants
                    </p>
                </div>

                {message && (
                    <div className={`mb-6 rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                        <p className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                            {message}
                        </p>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="bg-white shadow rounded-lg p-8 space-y-6">
                    <div>
                        <label htmlFor="display_name" className="block text-sm font-medium text-gray-700">
                            Display Name *
                        </label>
                        <input
                            type="text"
                            id="display_name"
                            required
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            placeholder="Dr. Jane Smith"
                            value={form.display_name}
                            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                        />
                        <p className="mt-1 text-sm text-gray-500">
                            This is how clients will see your name
                        </p>
                    </div>

                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                        <div>
                            <label htmlFor="consultant_type" className="block text-sm font-medium text-gray-700">
                                Consultant Type *
                            </label>
                            <select
                                id="consultant_type"
                                required
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={form.consultant_type}
                                onChange={(e) => setForm({ ...form, consultant_type: e.target.value as any })}
                            >
                                <option value="clinical">Clinical</option>
                                <option value="non_clinical">Non-Clinical</option>
                                <option value="wellness">Wellness</option>
                            </select>
                        </div>

                        <div>
                            <label htmlFor="highest_qualification" className="block text-sm font-medium text-gray-700">
                                Highest Qualification *
                            </label>
                            <input
                                type="text"
                                id="highest_qualification"
                                required
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                placeholder="e.g., MD, PhD, MSc"
                                value={form.highest_qualification}
                                onChange={(e) => setForm({ ...form, highest_qualification: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                        <div>
                            <label htmlFor="graduation_institution" className="block text-sm font-medium text-gray-700">
                                Graduation Institution
                            </label>
                            <input
                                type="text"
                                id="graduation_institution"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                placeholder="University Name"
                                value={form.graduation_institution || ""}
                                onChange={(e) => setForm({ ...form, graduation_institution: e.target.value })}
                            />
                        </div>

                        <div>
                            <label htmlFor="registration_body" className="block text-sm font-medium text-gray-700">
                                Registration Body
                            </label>
                            <input
                                type="text"
                                id="registration_body"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                placeholder="e.g., Medical Council"
                                value={form.registration_body || ""}
                                onChange={(e) => setForm({ ...form, registration_body: e.target.value })}
                            />
                        </div>
                    </div>

                    <div>
                        <label htmlFor="registration_number" className="block text-sm font-medium text-gray-700">
                            Registration Number
                        </label>
                        <input
                            type="text"
                            id="registration_number"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            placeholder="Professional registration number"
                            value={form.registration_number || ""}
                            onChange={(e) => setForm({ ...form, registration_number: e.target.value })}
                        />
                    </div>

                    <div>
                        <label htmlFor="specialties" className="block text-sm font-medium text-gray-700">
                            Specialties
                        </label>
                        <input
                            type="text"
                            id="specialties"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            placeholder="e.g., Weight Loss, Nutrition, Fitness Training"
                            value={form.specialties || ""}
                            onChange={(e) => setForm({ ...form, specialties: e.target.value })}
                        />
                    </div>

                    <div>
                        <label htmlFor="bio" className="block text-sm font-medium text-gray-700">
                            Bio
                        </label>
                        <textarea
                            id="bio"
                            rows={4}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            placeholder="Tell potential clients about your background, experience, and approach..."
                            value={form.bio || ""}
                            onChange={(e) => setForm({ ...form, bio: e.target.value })}
                        />
                    </div>

                    <div>
                        <label htmlFor="other_info" className="block text-sm font-medium text-gray-700">
                            Additional Information
                        </label>
                        <textarea
                            id="other_info"
                            rows={3}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            placeholder="Any other details you'd like to share..."
                            value={form.other_info || ""}
                            onChange={(e) => setForm({ ...form, other_info: e.target.value })}
                        />
                    </div>

                    <div>
                        <label htmlFor="documents" className="block text-sm font-medium text-gray-700">
                            Credentials & Certificates (PDF)
                        </label>
                        <input
                            type="file"
                            id="documents"
                            multiple
                            accept=".pdf"
                            className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                            onChange={handleFileChange}
                        />
                        <p className="mt-1 text-sm text-gray-500">
                            Upload your certifications, licenses, or credentials (optional)
                        </p>
                        {documents.length > 0 && (
                            <div className="mt-2">
                                <p className="text-sm text-gray-700">
                                    Selected: {documents.length} file(s)
                                </p>
                                <ul className="mt-1 text-xs text-gray-600 list-disc list-inside">
                                    {documents.map((doc, idx) => (
                                        <li key={idx}>{doc.name}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>

                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <h3 className="text-sm font-medium text-blue-900 mb-2">What happens next?</h3>
                        <ul className="text-sm text-blue-700 space-y-1 list-disc list-inside">
                            <li>Your application will be reviewed by our team</li>
                            <li>We'll verify your credentials and background</li>
                            <li>Once approved, you'll be able to accept client appointments</li>
                            <li>You'll receive an email notification about your application status</li>
                        </ul>
                    </div>

                    <div className="flex justify-between pt-4">
                        <Link
                            href="/dashboard"
                            className="inline-flex justify-center py-2 px-4 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                        >
                            Cancel
                        </Link>
                        <button
                            type="submit"
                            disabled={uploading || !form.display_name}
                            className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                        >
                            {uploading ? "Submitting..." : "Submit Application"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
