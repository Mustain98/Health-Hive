"use client";

import { useEffect, useState, FormEvent } from "react";
import { apiFetch, apiUpload } from "@/lib/api";
import type { ConsultantProfileRead, ConsultantProfileCreate, ConsultantDocumentRead } from "@/lib/types";

const SUPABASE_PROJECT_ID = "vavfkeoaalmibivqdzqd";
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || `https://${SUPABASE_PROJECT_ID}.supabase.co`;

function getDocumentUrl(bucket: string, path: string) {
    if (!path) return "#";
    if (path.startsWith("http")) return path;
    return `${SUPABASE_URL}/storage/v1/object/public/${bucket}/${path}`;
}

export default function ConsultantProfilePage() {
    const [profile, setProfile] = useState<ConsultantProfileRead | null>(null);
    const [documents, setDocuments] = useState<ConsultantDocumentRead[]>([]);

    // Profile Form State
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

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    // Document Upload State
    const [docType, setDocType] = useState("certificate");
    const [docIssuer, setDocIssuer] = useState("");
    const [docFile, setDocFile] = useState<File | null>(null);

    useEffect(() => {
        loadProfile();
    }, []);

    async function loadProfile() {
        try {
            const data = await apiFetch<ConsultantProfileRead>("/api/consultants/me/profile");
            setProfile(data);
            setForm({
                display_name: data.display_name,
                bio: data.bio || "",
                specialties: data.specialties || "",
                other_info: data.other_info || "",
                consultant_type: data.consultant_type,
                highest_qualification: data.highest_qualification,
                graduation_institution: data.graduation_institution || "",
                registration_body: data.registration_body || "",
                registration_number: data.registration_number || "",
            });

            // Load documents
            const docs = await apiFetch<ConsultantDocumentRead[]>(
                `/api/consultants/${data.id}/documents`
            ).catch(() => []);
            setDocuments(docs);
        } catch (error: any) {
            if (error.status !== 404) {
                console.error("Failed to load profile:", error);
            }
        } finally {
            setLoading(false);
        }
    }

    async function handleSaveProfile(e: FormEvent) {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        try {
            // Use PUT to upsert logic on backend
            const data = await apiFetch<ConsultantProfileRead>("/api/consultants/me/profile", {
                method: "PUT",
                body: form,
            });
            setProfile(data);
            setMessage("Profile saved successfully!");
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setSaving(false);
        }
    }

    async function handleUploadDocument(e: FormEvent) {
        e.preventDefault();
        if (!docFile || !profile) return;

        setUploading(true);
        setMessage(null);

        try {
            const formData = new FormData();
            formData.append("file", docFile);
            formData.append("consultant_profile_id", profile.id.toString());
            // Backend expects doc_type, issuer
            formData.append("doc_type", docType);
            formData.append("issuer", docIssuer);

            const doc = await apiUpload<ConsultantDocumentRead>("/api/consultants/me/documents", formData);

            setDocuments([doc, ...documents]); // Prepend new doc
            setMessage("Document uploaded successfully!");

            // Reset form
            setDocIssuer("");
            setDocFile(null);
        } catch (error: any) {
            setMessage(`Error uploading document: ${error.message}`);
        } finally {
            setUploading(false);
        }
    }

    if (loading) {
        return <div className="text-center py-12">Loading...</div>;
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Consultant Profile</h1>
                <p className="mt-2 text-sm text-gray-600">
                    Manage your professional details and credentials.
                </p>
                {profile?.is_verified && (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 mt-2">
                        ✓ Verified
                    </span>
                )}
            </div>

            {message && (
                <div className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                    <p className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                        {message}
                    </p>
                </div>
            )}

            {/* Profile Form */}
            <form onSubmit={handleSaveProfile} className="bg-white shadow rounded-lg p-6 space-y-6">
                <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                    <div className="sm:col-span-2">
                        <label className="block text-sm font-medium text-gray-700">Display Name *</label>
                        <input
                            type="text"
                            required
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.display_name}
                            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                        />
                    </div>

                    <div className="sm:col-span-2">
                        <label className="block text-sm font-medium text-gray-700">Bio</label>
                        <textarea
                            rows={3}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.bio || ""}
                            onChange={(e) => setForm({ ...form, bio: e.target.value })}
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700">Consultant Type</label>
                        <select
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
                        <label className="block text-sm font-medium text-gray-700">Highest Qualification *</label>
                        <input
                            type="text"
                            required
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.highest_qualification}
                            onChange={(e) => setForm({ ...form, highest_qualification: e.target.value })}
                            placeholder="e.g. BSc in Nutrition"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700">Graduation Institution</label>
                        <input
                            type="text"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.graduation_institution || ""}
                            onChange={(e) => setForm({ ...form, graduation_institution: e.target.value })}
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700">Registration Body</label>
                        <input
                            type="text"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.registration_body || ""}
                            onChange={(e) => setForm({ ...form, registration_body: e.target.value })}
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700">Registration Number</label>
                        <input
                            type="text"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.registration_number || ""}
                            onChange={(e) => setForm({ ...form, registration_number: e.target.value })}
                        />
                    </div>

                    <div className="sm:col-span-2">
                        <label className="block text-sm font-medium text-gray-700">Specialties</label>
                        <input
                            type="text"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.specialties || ""}
                            onChange={(e) => setForm({ ...form, specialties: e.target.value })}
                            placeholder="e.g. Weight Management, Sports Nutrition"
                        />
                    </div>

                    <div className="sm:col-span-2">
                        <label className="block text-sm font-medium text-gray-700">Other Info</label>
                        <textarea
                            rows={2}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.other_info || ""}
                            onChange={(e) => setForm({ ...form, other_info: e.target.value })}
                        />
                    </div>
                </div>

                <div className="flex justify-end">
                    <button
                        type="submit"
                        disabled={saving}
                        className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                    >
                        {saving ? "Saving..." : profile ? "Update Profile" : "Create Profile"}
                    </button>
                </div>
            </form>

            {/* Document Upload */}
            {profile && (
                <div className="bg-white shadow rounded-lg p-6 space-y-6">
                    <h2 className="text-lg font-medium text-gray-900">Upload Credentials</h2>

                    <form onSubmit={handleUploadDocument} className="space-y-4">
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Document Type</label>
                                <select
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                    value={docType}
                                    onChange={(e) => setDocType(e.target.value)}
                                >
                                    <option value="degree">Degree</option>
                                    <option value="certificate">Certificate</option>
                                    <option value="license">License</option>
                                    <option value="internship">Internship</option>
                                    <option value="experience">Experience</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Issuer</label>
                                <input
                                    type="text"
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                    value={docIssuer}
                                    onChange={(e) => setDocIssuer(e.target.value)}
                                    placeholder="e.g. University of Dhaka"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700">File (PDF) *</label>
                            <input
                                type="file"
                                accept=".pdf"
                                required
                                className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                                onChange={(e) => setDocFile(e.target.files?.[0] || null)}
                            />
                        </div>

                        <div className="flex justify-end">
                            <button
                                type="submit"
                                disabled={uploading || !docFile}
                                className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                            >
                                {uploading ? "Uploading..." : "Upload Document"}
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Documents List */}
            {documents.length > 0 && (
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Uploaded Documents</h2>
                    <div className="space-y-3">
                        {documents.map((doc) => (
                            <div key={doc.id} className="border border-gray-200 rounded-lg p-4">
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h3 className="text-sm font-medium text-gray-900 capitalize">
                                            {doc.doc_type}
                                        </h3>
                                        {doc.issuer && (
                                            <p className="text-sm text-gray-600">Issuer: {doc.issuer}</p>
                                        )}
                                        <p className="text-xs text-gray-500 mt-1">
                                            Uploaded: {new Date(doc.created_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <a
                                        href={getDocumentUrl(doc.bucket, doc.file_path)}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-sm font-medium text-blue-600 hover:text-blue-500 bg-blue-50 px-3 py-1 rounded"
                                    >
                                        View PDF
                                    </a>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}