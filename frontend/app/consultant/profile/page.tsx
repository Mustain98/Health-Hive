"use client";

import { useEffect, useState, FormEvent } from "react";
import { apiFetch, apiUpload } from "@/lib/api";
import type { ConsultantProfileRead, ConsultantProfileCreate, ConsultantDocumentRead } from "@/lib/types";

export default function ConsultantProfilePage() {
    const [profile, setProfile] = useState<ConsultantProfileRead | null>(null);
    const [documents, setDocuments] = useState<ConsultantDocumentRead[]>([]);
    const [form, setForm] = useState<ConsultantProfileCreate>({
        display_name: "",
        bio: "",
        specialties: "",
        other_info: "",
        // Add new fields
        phone: "",
        years_of_experience: undefined,
        qualifications: "",
        hourly_rate: undefined,
        consultation_duration_minutes: undefined,
        availability: "",
        profile_picture_url: "",
        linkedin_url: "",
        twitter_url: "",
        website_url: "",
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    // Document upload form
    const [docTitle, setDocTitle] = useState("");
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
                // Add new fields
                phone: data.phone || "",
                years_of_experience: data.years_of_experience,
                qualifications: data.qualifications || "",
                hourly_rate: data.hourly_rate,
                consultation_duration_minutes: data.consultation_duration_minutes,
                availability: data.availability || "",
                profile_picture_url: data.profile_picture_url || "",
                linkedin_url: data.linkedin_url || "",
                twitter_url: data.twitter_url || "",
                website_url: data.website_url || "",
            });

            // Load documents (from consultant's own profile ID)
            const docs = await apiFetch<ConsultantDocumentRead[]>(
                `/api/consultants/${data.id}/documents`
            ).catch(() => []);
            setDocuments(docs);
        } catch (error: any) {
            // 404 is expected if no profile exists
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
            formData.append("title", docTitle);
            formData.append("issuer", docIssuer);
            formData.append("doc_type", "certificate");

            const doc = await apiUpload<ConsultantDocumentRead>("/api/consultants/me/documents", formData);

            setDocuments([...documents, doc]);
            setMessage("Document uploaded successfully!");
            setDocTitle("");
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
                    Manage your consultant profile and credentials
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
            <form onSubmit={handleSaveProfile} className="space-y-8">
                {/* Basic Information */}
                <div className="bg-white shadow rounded-lg p-6 space-y-6">
                    <h2 className="text-lg font-medium text-gray-900">Basic Information</h2>
                    
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Display Name *
                        </label>
                        <input
                            type="text"
                            required
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.display_name}
                            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                            placeholder="Dr. Jane Smith"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700">Bio</label>
                        <textarea
                            rows={4}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.bio || ""}
                            onChange={(e) => setForm({ ...form, bio: e.target.value })}
                            placeholder="Tell clients about your background and experience..."
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700">Specialties</label>
                        <input
                            type="text"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.specialties || ""}
                            onChange={(e) => setForm({ ...form, specialties: e.target.value })}
                            placeholder="e.g., Weight Loss, Nutrition, Fitness"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700">Other Information</label>
                        <textarea
                            rows={3}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.other_info || ""}
                            onChange={(e) => setForm({ ...form, other_info: e.target.value })}
                            placeholder="Additional details..."
                        />
                    </div>
                </div>

                {/* Contact Information */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Contact Information</h2>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Phone Number</label>
                        <input
                            type="tel"
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                            value={form.phone || ""}
                            onChange={(e) => setForm({ ...form, phone: e.target.value })}
                            placeholder="+1 (555) 123-4567"
                        />
                    </div>
                </div>

                {/* Professional Details */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Professional Details</h2>
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Years of Experience</label>
                            <input
                                type="number"
                                min="0"
                                max="50"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={form.years_of_experience || ""}
                                onChange={(e) => setForm({ ...form, years_of_experience: e.target.value ? Number(e.target.value) : undefined })}
                                placeholder="10"
                            />
                        </div>
                        <div className="sm:col-span-2">
                            <label className="block text-sm font-medium text-gray-700">Qualifications</label>
                            <textarea
                                rows={3}
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={form.qualifications || ""}
                                onChange={(e) => setForm({ ...form, qualifications: e.target.value })}
                                placeholder="e.g., PhD in Nutrition Science, Registered Dietitian, Certified Health Coach"
                            />
                        </div>
                    </div>
                </div>

                {/* Consultation Information */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Consultation Information</h2>
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Hourly Rate ($)</label>
                            <input
                                type="number"
                                min="0"
                                step="0.01"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={form.hourly_rate || ""}
                                onChange={(e) => setForm({ ...form, hourly_rate: e.target.value ? Number(e.target.value) : undefined })}
                                placeholder="150.00"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Session Duration (minutes)</label>
                            <input
                                type="number"
                                min="15"
                                step="15"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={form.consultation_duration_minutes || ""}
                                onChange={(e) => setForm({ ...form, consultation_duration_minutes: e.target.value ? Number(e.target.value) : undefined })}
                                placeholder="60"
                            />
                        </div>
                        <div className="sm:col-span-2">
                            <label className="block text-sm font-medium text-gray-700">Availability</label>
                            <textarea
                                rows={2}
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={form.availability || ""}
                                onChange={(e) => setForm({ ...form, availability: e.target.value })}
                                placeholder="e.g., Mon-Fri 9AM-5PM EST, Weekends by appointment"
                            />
                        </div>
                    </div>
                </div>

                {/* Profile & Social Links */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Profile & Social Links</h2>
                    <div className="grid grid-cols-1 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Profile Picture URL</label>
                            <input
                                type="url"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={form.profile_picture_url || ""}
                                onChange={(e) => setForm({ ...form, profile_picture_url: e.target.value })}
                                placeholder="https://example.com/photo.jpg"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">LinkedIn Profile</label>
                            <input
                                type="url"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={form.linkedin_url || ""}
                                onChange={(e) => setForm({ ...form, linkedin_url: e.target.value })}
                                placeholder="https://linkedin.com/in/yourprofile"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Twitter Profile</label>
                            <input
                                type="url"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={form.twitter_url || ""}
                                onChange={(e) => setForm({ ...form, twitter_url: e.target.value })}
                                placeholder="https://twitter.com/yourhandle"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Website</label>
                            <input
                                type="url"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={form.website_url || ""}
                                onChange={(e) => setForm({ ...form, website_url: e.target.value })}
                                placeholder="https://yourwebsite.com"
                            />
                        </div>
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
                    <h2 className="text-lg font-medium text-gray-900">Upload Certificate</h2>

                    <form onSubmit={handleUploadDocument} className="space-y-4">
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Title *</label>
                                <input
                                    type="text"
                                    required
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                    value={docTitle}
                                    onChange={(e) => setDocTitle(e.target.value)}
                                    placeholder="e.g., Certified Nutritionist"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Issuer</label>
                                <input
                                    type="text"
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                    value={docIssuer}
                                    onChange={(e) => setDocIssuer(e.target.value)}
                                    placeholder="e.g., International Board of Nutrition"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700">Document (PDF) *</label>
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
                                <h3 className="text-sm font-medium text-gray-900">{doc.title}</h3>
                                {doc.issuer && (
                                    <p className="text-sm text-gray-600 mt-1">Issuer: {doc.issuer}</p>
                                )}
                                <p className="text-sm text-gray-500 mt-1">
                                    Uploaded: {new Date(doc.created_at).toLocaleDateString()}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}