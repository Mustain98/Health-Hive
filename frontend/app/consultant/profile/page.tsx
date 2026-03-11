"use client";

import { useEffect, useState, FormEvent } from "react";
import { apiFetch, apiUpload } from "@/lib/api";
import type {
    ConsultantProfileRead,
    ConsultantProfileCreate,
    ConsultantDocumentRead,
    AvailabilityRuleRead,
    AvailabilityRuleCreate
} from "@/lib/types";

const SUPABASE_PROJECT_ID = "vavfkeoaalmibivqdzqd";
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || `https://${SUPABASE_PROJECT_ID}.supabase.co`;

function getDocumentUrl(bucket: string, path: string) {
    if (!path) return "#";
    if (path.startsWith("http")) return path;
    return `${SUPABASE_URL}/storage/v1/object/public/${bucket}/${path}`;
}

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

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

    // Availability Rules State
    const [rules, setRules] = useState<AvailabilityRuleRead[]>([]);
    const [showAddModal, setShowAddModal] = useState(false);
    const [selectedDay, setSelectedDay] = useState(0);
    const [startTime, setStartTime] = useState("09:00");
    const [endTime, setEndTime] = useState("17:00");
    const [consultationDuration, setConsultationDuration] = useState(30);
    const [submittingRule, setSubmittingRule] = useState(false);

    useEffect(() => {
        loadProfile();
        loadRules();
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
                `/api/consultants/${data.user_id}/documents`
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

    async function loadRules() {
        try {
            const data = await apiFetch<AvailabilityRuleRead[]>("/api/consultants/me/availability");
            setRules(data);
        } catch (error: any) {
            console.error("Failed to load availability rules:", error);
        }
    }

    async function handleAddRule() {
        if (!startTime || !endTime) {
            setMessage("Please fill in all fields");
            return;
        }

        setSubmittingRule(true);
        setMessage(null);

        try {
            const newRule: AvailabilityRuleCreate = {
                day_of_week: selectedDay,
                start_time: startTime,
                end_time: endTime,
                timezone: "Asia/Dhaka",
                consultation_duration: consultationDuration,
            };

            await apiFetch("/api/consultants/me/availability", {
                method: "POST",
                body: newRule,
            });

            setMessage("Time slot added successfully");
            setShowAddModal(false);
            setStartTime("09:00");
            setEndTime("17:00");
            setConsultationDuration(30);
            await loadRules();
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setSubmittingRule(false);
        }
    }

    async function handleDeleteRule(ruleId: string) {
        if (!confirm("Are you sure you want to delete this time slot?")) return;

        setMessage(null);
        try {
            await apiFetch(`/api/consultants/me/availability/${ruleId}`, {
                method: "DELETE",
            });
            setMessage("Time slot deleted");
            await loadRules();
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        }
    }

    async function handleToggleActive(rule: AvailabilityRuleRead) {
        setMessage(null);
        try {
            await apiFetch(`/api/consultants/me/availability/${rule.id}`, {
                method: "PATCH",
                body: { is_active: !rule.is_active },
            });
            await loadRules();
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
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
            formData.append("consultant_profile_id", profile.user_id);
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
                                        <h3 className="text-sm font-medium text-gray-900 capitalize flex items-center gap-2">
                                            {doc.doc_type}
                                            {doc.is_verified ? (
                                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">✓ Verified</span>
                                            ) : (
                                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">! Unverified</span>
                                            )}
                                        </h3>
                                        {doc.issuer && (
                                            <p className="text-sm text-gray-600">Issuer: {doc.issuer}</p>
                                        )}
                                        {doc.verification_note && (
                                            <p className="text-sm text-blue-600 mt-1 italic">Note: {doc.verification_note}</p>
                                        )}
                                        <p className="text-xs text-gray-500 mt-1">
                                            Uploaded: {new Date(doc.created_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <a
                                        href={doc.file_url || getDocumentUrl(doc.bucket, doc.file_path)}
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

            {/* Availability Rules */}
            {profile && (
                <div className="bg-white shadow rounded-lg p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-medium text-gray-900">Availability Settings</h2>
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
                        >
                            + Add Time Slot
                        </button>
                    </div>

                    <p className="text-sm text-gray-600 mb-4">
                        Set your weekly availability for consultations
                    </p>

                    <div className="space-y-4">
                        {DAYS.map((dayName, dayIndex) => {
                            const dayRules = rules.filter((r) => r.day_of_week === dayIndex);
                            return (
                                <div key={dayIndex} className="border-b border-gray-200 pb-4 last:border-0">
                                    <h3 className="font-medium text-gray-900 mb-2">{dayName}</h3>

                                    {dayRules.length === 0 ? (
                                        <p className="text-sm text-gray-500">No availability set</p>
                                    ) : (
                                        <div className="space-y-2">
                                            {dayRules.map((rule) => (
                                                <div
                                                    key={rule.id}
                                                    className={`flex items-center gap-3 p-3 rounded-md border ${rule.is_active
                                                        ? "bg-green-50 border-green-200"
                                                        : "bg-gray-50 border-gray-200 opacity-60"
                                                        }`}
                                                >
                                                    <div className="flex-1">
                                                        <div className="font-medium text-gray-900">
                                                            {rule.start_time} – {rule.end_time}
                                                        </div>
                                                        <div className="text-xs text-gray-500">
                                                            Duration: {rule.consultation_duration} min
                                                            {!rule.is_active && " (Inactive)"}
                                                        </div>
                                                    </div>

                                                    <div className="flex gap-2">
                                                        <button
                                                            onClick={() => handleToggleActive(rule)}
                                                            className="px-3 py-1 text-sm rounded-md bg-white border border-gray-300 hover:bg-gray-50"
                                                        >
                                                            {rule.is_active ? "Disable" : "Enable"}
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeleteRule(rule.id)}
                                                            className="px-3 py-1 text-sm rounded-md text-red-700 bg-red-100 hover:bg-red-200"
                                                        >
                                                            Delete
                                                        </button>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Add Availability Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">Add Availability Slot</h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Day</label>
                                <select
                                    value={selectedDay}
                                    onChange={(e) => setSelectedDay(parseInt(e.target.value))}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                                >
                                    {DAYS.map((day, idx) => (
                                        <option key={idx} value={idx}>
                                            {day}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Start Time</label>
                                <input
                                    type="time"
                                    value={startTime}
                                    onChange={(e) => setStartTime(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">End Time</label>
                                <input
                                    type="time"
                                    value={endTime}
                                    onChange={(e) => setEndTime(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Consultation Duration (min)</label>
                                <input
                                    type="number"
                                    value={consultationDuration}
                                    onChange={(e) => setConsultationDuration(parseInt(e.target.value))}
                                    min={5}
                                    max={240}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => setShowAddModal(false)}
                                disabled={submittingRule}
                                className="px-4 py-2 text-sm font-medium rounded-md text-gray-700 bg-gray-100 hover:bg-gray-200"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleAddRule}
                                disabled={submittingRule}
                                className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60"
                            >
                                {submittingRule ? "Adding..." : "Add Slot"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
